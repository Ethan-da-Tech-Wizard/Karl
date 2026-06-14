#!/usr/bin/env python3
"""
Karl Log Decryption Utility
===========================
Decrypts and decompresses archived trace logs (.jsonl.enc) for auditing or training.

Requires:
- The bridge token (via prompt or KARL_BRIDGE_TOKEN env var)
- To be run on the SAME hardware that encrypted the logs (for salt matching)
"""

import os
import sys
import json
import gzip
import base64
import hashlib
import shutil
import argparse
import getpass
import platform

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import psutil
    from cryptography.fernet import Fernet
    from core.hardware_scout import get_cpu_flags
    from app.utils.keychain_manager import load_cached_token, save_cached_token
except ImportError as e:
    print(f"Error: Missing dependencies. Please ensure you are running in the Karl venv. ({e})")
    sys.exit(1)

def derive_key(token: str) -> bytes:
    """Recreates the exact key derivation from TraceLogger."""
    try:
        # 1. Gather stable hardware salt (must match TraceLogger exactly)
        total_ram = psutil.virtual_memory().total
        total_storage = shutil.disk_usage(os.getcwd()).total
        cpu_flags = "".join(get_cpu_flags())
        os_name = platform.system()
        
        salt_seed = f"{total_ram}-{total_storage}-{cpu_flags}-{os_name}"
        
        # 2. PBKDF2 stretching
        k = hashlib.pbkdf2_hmac(
            'sha256', 
            token.encode(), 
            salt_seed.encode(), 
            100000
        )
        return base64.urlsafe_b64encode(k)
    except Exception as e:
        print(f"Error during key derivation: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Decrypt Karl encrypted trace logs.")
    parser.add_argument("--input", "-i", required=True, help="Path to the .enc log file.")
    parser.add_argument("--output", "-o", required=True, help="Path to save the decrypted .jsonl file.")
    parser.add_argument("--token", "-t", help="Bridge token (optional, will prompt if omitted).")
    
    args = parser.parse_args()

    # 1. Get Token (check env, then keychain, then prompt)
    token = args.token or os.environ.get("KARL_BRIDGE_TOKEN")
    if not token:
        token = load_cached_token()
        if token:
            print("Using cached token from OS keychain.")
            
    if not token:
        token = getpass.getpass("Enter Karl Bridge Token: ")
    
    if not token:
        print("Error: No token provided.")
        sys.exit(1)

    # 2. Derive Key
    key = derive_key(token)
    
    # 3. Decrypt and Decompress
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    try:
        print(f"Decrypting {args.input}...")
        
        with open(args.input, 'rb') as f_in:
            encrypted_data = f_in.read()
        
        fernet = Fernet(key)
        try:
            gzipped_data = fernet.decrypt(encrypted_data)
        except Exception:
            # Likely invalid token or salt mismatch
            print("\nDecryption failed: Invalid bridge token or hardware profile mismatch.")
            sys.exit(1)
            
        print("Decompressing payload...")
        try:
            plaintext = gzip.decompress(gzipped_data)
        except Exception as e:
            print(f"Error: Decryption succeeded but decompression failed. The file may be corrupt. ({e})")
            sys.exit(1)
            
        # 3b. Successful manual auth -> cache in keyring
        if not args.token and not os.environ.get("KARL_BRIDGE_TOKEN"):
             save_cached_token(token)

        # 4. Write Output
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, 'wb') as f_out:
            f_out.write(plaintext)
            
        print(f"Decryption complete: {args.output}")
        sys.exit(0)
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
