-- Lightweight Karl bridge client for Neovim.
--
-- Usage:
--   :luafile neovim/karl.lua
--   :KarlAsk
--   visually select text, then :KarlExplain
--
-- This client prefers a websocat wrapper for Karl's default WSS endpoint and
-- retains a vim.loop.new_tcp() WebSocket implementation for plain ws:// test
-- proxies. Neovim/libuv does not provide TLS primitives directly.

local uv = vim.loop or vim.uv

local Karl = {
  host = "127.0.0.1",
  port = 8080,
  token_path = "data/bridge_token.json",
  workspace_path = vim.fn.getcwd(),
  socket = nil,
  job = nil,
  transport = "auto", -- "auto", "websocat", or "tcp"
  connected = false,
  connecting = false,
  handshake_done = false,
  recv_buffer = "",
  pending = {},
  next_id = 1,
  float_buf = nil,
  float_win = nil,
  response_line = 0,
}

local bit = bit32 or bit

local function bxor(a, b)
  return bit.bxor(a, b)
end

local function band(a, b)
  return bit.band(a, b)
end

local function rshift(a, b)
  return bit.rshift(a, b)
end

local function lshift(a, b)
  return bit.lshift(a, b)
end

local function schedule(fn)
  vim.schedule(fn)
end

local function notify(msg, level)
  schedule(function()
    vim.notify(msg, level or vim.log.levels.INFO, { title = "Karl" })
  end)
end

local function read_file(path)
  local f = io.open(path, "r")
  if not f then
    return nil
  end
  local data = f:read("*a")
  f:close()
  return data
end

local function read_token()
  local raw = read_file(Karl.token_path)
  if not raw then
    return ""
  end
  local ok, decoded = pcall(vim.json.decode, raw)
  if ok and type(decoded) == "table" then
    return decoded.token or ""
  end
  return ""
end

local function rand_bytes(n)
  math.randomseed(os.time() + vim.fn.getpid())
  local t = {}
  for i = 1, n do
    t[i] = string.char(math.random(0, 255))
  end
  return table.concat(t)
end

local function websocket_key()
  return vim.base64.encode(rand_bytes(16))
end

local function ensure_float()
  if Karl.float_buf and vim.api.nvim_buf_is_valid(Karl.float_buf) then
    if Karl.float_win and vim.api.nvim_win_is_valid(Karl.float_win) then
      return
    end
  else
    Karl.float_buf = vim.api.nvim_create_buf(false, true)
    vim.bo[Karl.float_buf].bufhidden = "wipe"
    vim.bo[Karl.float_buf].filetype = "markdown"
  end

  local width = math.floor(vim.o.columns * 0.72)
  local height = math.floor(vim.o.lines * 0.55)
  local row = math.floor((vim.o.lines - height) / 2)
  local col = math.floor((vim.o.columns - width) / 2)
  Karl.float_win = vim.api.nvim_open_win(Karl.float_buf, true, {
    relative = "editor",
    row = row,
    col = col,
    width = width,
    height = height,
    border = "rounded",
    title = " Karl ",
    title_pos = "center",
    style = "minimal",
  })
end

local function reset_float(title)
  schedule(function()
    ensure_float()
    vim.api.nvim_buf_set_lines(Karl.float_buf, 0, -1, false, {
      "# " .. (title or "Karl"),
      "",
      "## Response",
      "",
    })
    Karl.response_line = 3
  end)
end

local function append_to_float(text)
  if not text or text == "" then
    return
  end
  schedule(function()
    ensure_float()
    local lines = vim.split(text, "\n", { plain = true })
    local current = vim.api.nvim_buf_get_lines(Karl.float_buf, Karl.response_line, Karl.response_line + 1, false)[1] or ""
    lines[1] = current .. lines[1]
    vim.api.nvim_buf_set_lines(Karl.float_buf, Karl.response_line, Karl.response_line + 1, false, lines)
    Karl.response_line = Karl.response_line + #lines - 1
    if Karl.float_win and vim.api.nvim_win_is_valid(Karl.float_win) then
      vim.api.nvim_win_set_cursor(Karl.float_win, { Karl.response_line + 1, 0 })
    end
  end)
end

local function append_status(text)
  schedule(function()
    ensure_float()
    vim.api.nvim_buf_set_lines(Karl.float_buf, -1, -1, false, { "", "> " .. text })
  end)
end

local function encode_ws_frame(payload)
  local len = #payload
  local mask = rand_bytes(4)
  local header = { string.char(0x81) }
  if len < 126 then
    table.insert(header, string.char(0x80 + len))
  elseif len < 65536 then
    table.insert(header, string.char(0x80 + 126))
    table.insert(header, string.char(rshift(len, 8), band(len, 0xff)))
  else
    table.insert(header, string.char(0x80 + 127))
    table.insert(header, string.char(0, 0, 0, 0))
    table.insert(header, string.char(
      band(rshift(len, 24), 0xff),
      band(rshift(len, 16), 0xff),
      band(rshift(len, 8), 0xff),
      band(len, 0xff)
    ))
  end
  table.insert(header, mask)

  local masked = {}
  for i = 1, len do
    local m = mask:byte(((i - 1) % 4) + 1)
    masked[i] = string.char(bxor(payload:byte(i), m))
  end
  table.insert(header, table.concat(masked))
  return table.concat(header)
end

local function try_decode_frame(buffer)
  if #buffer < 2 then
    return nil, buffer
  end
  local b1, b2 = buffer:byte(1, 2)
  local opcode = band(b1, 0x0f)
  local masked = band(b2, 0x80) ~= 0
  local len = band(b2, 0x7f)
  local pos = 3
  if len == 126 then
    if #buffer < 4 then
      return nil, buffer
    end
    local a, b = buffer:byte(3, 4)
    len = a * 256 + b
    pos = 5
  elseif len == 127 then
    if #buffer < 10 then
      return nil, buffer
    end
    local b7, b8, b9, b10 = buffer:byte(7, 10)
    len = lshift(b7, 24) + lshift(b8, 16) + lshift(b9, 8) + b10
    pos = 11
  end

  local mask
  if masked then
    if #buffer < pos + 3 then
      return nil, buffer
    end
    mask = buffer:sub(pos, pos + 3)
    pos = pos + 4
  end

  if #buffer < pos + len - 1 then
    return nil, buffer
  end

  local payload = buffer:sub(pos, pos + len - 1)
  local rest = buffer:sub(pos + len)
  if masked then
    local unmasked = {}
    for i = 1, #payload do
      local m = mask:byte(((i - 1) % 4) + 1)
      unmasked[i] = string.char(bxor(payload:byte(i), m))
    end
    payload = table.concat(unmasked)
  end
  return { opcode = opcode, payload = payload }, rest
end

local function send_raw(payload)
  if Karl.job then
    vim.fn.chansend(Karl.job, payload .. "\n")
    return true
  end
  if not Karl.socket or not Karl.connected then
    notify("Karl bridge is not connected.", vim.log.levels.WARN)
    return false
  end
  Karl.socket:write(encode_ws_frame(payload))
  return true
end

local function bridge_url()
  local token = read_token()
  local scheme = Karl.transport == "tcp" and "ws" or "wss"
  local url = scheme .. "://" .. Karl.host .. ":" .. tostring(Karl.port) .. "/"
  if token ~= "" then
    url = url .. "?token=" .. token
  end
  return url
end

local function rpc(method, params, cb)
  local id = Karl.next_id
  Karl.next_id = Karl.next_id + 1
  if cb then
    Karl.pending[id] = cb
  end
  return send_raw(vim.json.encode({
    jsonrpc = "2.0",
    id = id,
    method = method,
    params = params or {},
  }))
end

local function handle_message(payload)
  local ok, msg = pcall(vim.json.decode, payload)
  if not ok or type(msg) ~= "table" then
    append_status("Malformed bridge frame.")
    return
  end

  if msg.id and Karl.pending[msg.id] then
    local cb = Karl.pending[msg.id]
    Karl.pending[msg.id] = nil
    cb(msg)
    return
  end

  if msg.error then
    append_status("Error: " .. (msg.error.message or "unknown"))
    return
  end

  local method = msg.method
  local params = msg.params or {}
  if method == "chat_response_token" then
    append_to_float(params.token or "")
  elseif method == "chat_thought_token" then
    -- Keep the main floating pane focused on answer tokens. Uncomment this to
    -- show reasoning tokens as well.
    -- append_to_float(params.token or "")
  elseif method == "chat_finished" then
    append_status("complete")
  elseif method == "status_update" then
    append_status(params.message or "")
  elseif method == "finished_swarm" then
    append_status((params.success and "swarm complete: " or "swarm failed: ") .. (params.summary or ""))
  end
end

local function process_ws_data(data)
  Karl.recv_buffer = Karl.recv_buffer .. data
  while true do
    local frame
    frame, Karl.recv_buffer = try_decode_frame(Karl.recv_buffer)
    if not frame then
      return
    end
    if frame.opcode == 0x1 then
      handle_message(frame.payload)
    elseif frame.opcode == 0x8 then
      Karl.connected = false
      notify("Karl bridge closed the connection.", vim.log.levels.WARN)
      return
    end
  end
end

local function on_read(err, data)
  if err then
    notify("Karl bridge read error: " .. err, vim.log.levels.ERROR)
    return
  end
  if not data then
    Karl.connected = false
    return
  end

  if not Karl.handshake_done then
    Karl.recv_buffer = Karl.recv_buffer .. data
    local header_end = Karl.recv_buffer:find("\r\n\r\n", 1, true)
    if not header_end then
      return
    end
    local headers = Karl.recv_buffer:sub(1, header_end + 3)
    local rest = Karl.recv_buffer:sub(header_end + 4)
    Karl.recv_buffer = ""
    if not headers:match("^HTTP/1%.1 101") and not headers:match("^HTTP/1%.0 101") then
      notify("Karl bridge rejected WebSocket handshake.", vim.log.levels.ERROR)
      return
    end
    Karl.handshake_done = true
    Karl.connected = true
    Karl.connecting = false
    notify("Karl bridge connected.")
    rpc("get_runtime_status", {}, function() end)
    if #rest > 0 then
      process_ws_data(rest)
    end
    return
  end

  process_ws_data(data)
end

function Karl.connect(cb)
  if Karl.connected then
    if cb then cb(true) end
    return
  end
  if Karl.connecting then
    vim.defer_fn(function()
      Karl.connect(cb)
    end, 100)
    return
  end

  if Karl.transport ~= "tcp" and vim.fn.executable("websocat") == 1 then
    Karl.connecting = true
    local stdout_buf = ""
    Karl.job = vim.fn.jobstart({ "websocat", "-k", bridge_url() }, {
      stdout_buffered = false,
      stderr_buffered = false,
      on_stdout = function(_, data, _)
        if not data then
          return
        end
        for _, chunk in ipairs(data) do
          if chunk ~= "" then
            stdout_buf = stdout_buf .. chunk
            local ok, decoded = pcall(vim.json.decode, stdout_buf)
            if ok and type(decoded) == "table" then
              handle_message(stdout_buf)
              stdout_buf = ""
            end
          end
        end
      end,
      on_stderr = function(_, data, _)
        if data then
          for _, line in ipairs(data) do
            if line and line ~= "" then
              append_status(line)
            end
          end
        end
      end,
      on_exit = function(_, code, _)
        Karl.connected = false
        Karl.connecting = false
        Karl.job = nil
        if code ~= 0 then
          notify("Karl websocat bridge exited with code " .. tostring(code), vim.log.levels.WARN)
        end
      end,
    })
    if Karl.job <= 0 then
      Karl.job = nil
      Karl.connecting = false
      notify("Failed to start websocat. Falling back to raw TCP ws://.", vim.log.levels.WARN)
    else
      Karl.connected = true
      Karl.connecting = false
      notify("Karl bridge connected through websocat.")
      rpc("get_runtime_status", {}, function() end)
      if cb then cb(true) end
      return
    end
  end

  Karl.connecting = true
  Karl.handshake_done = false
  Karl.recv_buffer = ""
  Karl.socket = uv.new_tcp()
  Karl.socket:connect(Karl.host, Karl.port, function(err)
    if err then
      Karl.connecting = false
      notify("Karl bridge connection failed: " .. err, vim.log.levels.ERROR)
      if cb then cb(false) end
      return
    end

    local token = read_token()
    local path = "/"
    if token ~= "" then
      path = "/?token=" .. vim.fn.escape(token, "%#?&=+ ")
    end
    local request = table.concat({
      "GET " .. path .. " HTTP/1.1",
      "Host: " .. Karl.host .. ":" .. Karl.port,
      "Upgrade: websocket",
      "Connection: Upgrade",
      "Sec-WebSocket-Key: " .. websocket_key(),
      "Sec-WebSocket-Version: 13",
      "",
      "",
    }, "\r\n")
    Karl.socket:read_start(on_read)
    Karl.socket:write(request)
    if cb then
      vim.defer_fn(function()
        cb(Karl.connected)
      end, 500)
    end
  end)
end

local function buffer_text()
  return table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
end

local function visual_selection()
  local s = vim.fn.getpos("'<")
  local e = vim.fn.getpos("'>")
  local start_row, start_col = s[2] - 1, s[3] - 1
  local end_row, end_col = e[2] - 1, e[3]
  if start_row < 0 or end_row < 0 then
    return ""
  end
  local lines = vim.api.nvim_buf_get_text(0, start_row, start_col, end_row, end_col, {})
  return table.concat(lines, "\n")
end

local function submit_chat(message)
  Karl.connect(function(ok)
    if not ok then
      notify("Karl bridge is unavailable.", vim.log.levels.ERROR)
      return
    end
    reset_float("Karl Ask")
    rpc("submit_chat", {
      message = message,
      workspace_path = Karl.workspace_path,
      hyperparams = {
        temperature = 0.7,
        top_p = 0.95,
        max_tokens = 2048,
        rag_enabled = false,
      },
    }, function(msg)
      if msg.error then
        append_status("Error: " .. (msg.error.message or "submit_chat failed"))
      else
        append_status("started")
      end
    end)
  end)
end

local function submit_task(objective)
  Karl.connect(function(ok)
    if not ok then
      notify("Karl bridge is unavailable.", vim.log.levels.ERROR)
      return
    end
    reset_float("Karl Swarm")
    rpc("submit_task", {
      objective = objective,
      workspace_path = Karl.workspace_path,
      test_command = "python -m pytest",
      hyperparams = {
        temperature = 0.3,
        top_p = 0.9,
        max_tokens = 2048,
      },
    }, function(msg)
      if msg.error then
        append_status("Error: " .. (msg.error.message or "submit_task failed"))
      else
        append_status("swarm started")
      end
    end)
  end)
end

function Karl.ask()
  vim.ui.input({ prompt = "Karl question: " }, function(question)
    if not question or question == "" then
      return
    end
    local msg = table.concat({
      question,
      "",
      "Current buffer:",
      "```",
      buffer_text(),
      "```",
    }, "\n")
    submit_chat(msg)
  end)
end

function Karl.explain()
  local selected = visual_selection()
  if selected == "" then
    notify("No visual selection found.", vim.log.levels.WARN)
    return
  end
  submit_task(table.concat({
    "Explain the following selected code or text. Do not edit files unless explicitly necessary.",
    "",
    "Selection:",
    "```",
    selected,
    "```",
  }, "\n"))
end

function Karl.setup(opts)
  opts = opts or {}
  Karl.host = opts.host or Karl.host
  Karl.port = opts.port or Karl.port
  Karl.token_path = opts.token_path or Karl.token_path
  Karl.transport = opts.transport or Karl.transport
  Karl.workspace_path = opts.workspace_path or vim.fn.getcwd()
  vim.api.nvim_create_user_command("KarlAsk", Karl.ask, {})
  vim.api.nvim_create_user_command("KarlExplain", Karl.explain, { range = true })
end

Karl.setup()

return Karl
