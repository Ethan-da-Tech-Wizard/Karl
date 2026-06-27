import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.event_broker import EventBroker

def test_event_broker_thread_safety():
    broker = EventBroker.get_instance()
    
    received_messages = []
    received_lock = threading.Lock()
    
    def on_event(data):
        with received_lock:
            received_messages.append(data)
            
    broker.subscribe("test:thread_safety", on_event)
    
    threads = []
    num_threads = 10
    messages_per_thread = 100
    
    def publisher(thread_id):
        for i in range(messages_per_thread):
            broker.publish("test:thread_safety", {"thread_id": thread_id, "index": i})
            
    for t_id in range(num_threads):
        t = threading.Thread(target=publisher, args=(t_id,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Total messages received should be exactly 1000
    assert len(received_messages) == num_threads * messages_per_thread
    
    # Clean up subscriber
    broker.unsubscribe("test:thread_safety", on_event)
