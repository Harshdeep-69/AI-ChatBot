import tkinter as tk
from tkinter import scrolledtext
import requests
import threading
import json
import queue

# 🧠 Chat memory
messages = [
    {"role": "system", "content": "You are a fast, concise AI assistant. Give short and useful answers."}
]

MAX_MEMORY = 6

def trim_memory():
    global messages
    if len(messages) > MAX_MEMORY:
        messages[:] = [messages[0]] + messages[-(MAX_MEMORY - 1):]


# 🔥 Thread-safe queue
stream_queue = queue.Queue()


# 🤖 STREAMING AI RESPONSE
def stream_ai_response(user_input):
    messages.append({"role": "user", "content": user_input})

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "phi3:latest",
                "messages": messages,
                "stream": True,
                "options": {"num_predict": 120}
            },
            stream=True,
            timeout=None
        )

        if response.status_code != 200:
            stream_queue.put(f"⚠️ {response.text}")
            return

        full_reply = ""

        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))

                if "message" in data:
                    chunk = data["message"]["content"]
                    full_reply += chunk
                    stream_queue.put(chunk)

        messages.append({"role": "assistant", "content": full_reply})
        trim_memory()

    except Exception as e:
        stream_queue.put(f"\n❌ Error: {str(e)}")

    # signal end
    stream_queue.put(None)


# 💬 UI updater loop (runs every 50ms)
def process_stream():
    try:
        while True:
            chunk = stream_queue.get_nowait()

            if chunk is None:
                finish_ui()
                return

            chat_box.config(state=tk.NORMAL)

            # remove "Typing..." only once
            if "Typing..." in chat_box.get("end-3l", "end-1l"):
                chat_box.delete("end-2l", "end-1l")

            chat_box.insert(tk.END, chunk, "bot")
            chat_box.config(state=tk.DISABLED)
            chat_box.yview(tk.END)

    except queue.Empty:
        pass

    window.after(50, process_stream)


def finish_ui():
    chat_box.config(state=tk.NORMAL)
    chat_box.insert(tk.END, "\n\n")
    chat_box.config(state=tk.DISABLED)

    entry.config(state=tk.NORMAL)
    send_btn.config(state=tk.NORMAL)
    entry.focus()


# 📤 Send message
def send_message():
    user_msg = entry.get().strip()
    if not user_msg:
        return

    chat_box.config(state=tk.NORMAL)
    chat_box.insert(tk.END, f"\nYou:\n{user_msg}\n\nBot:\n", "user")
    chat_box.insert(tk.END, "Typing...\n", "typing")
    chat_box.config(state=tk.DISABLED)
    chat_box.yview(tk.END)

    entry.delete(0, tk.END)
    entry.config(state=tk.DISABLED)
    send_btn.config(state=tk.DISABLED)

    threading.Thread(target=stream_ai_response, args=(user_msg,), daemon=True).start()
    process_stream()


# 🖥️ UI setup
window = tk.Tk()
window.title("💬 AI Chatbot")
window.geometry("500x650")
window.configure(bg="#1e1e1e")

chat_box = scrolledtext.ScrolledText(
    window,
    wrap=tk.WORD,
    font=("Segoe UI", 11),
    bg="#252526",
    fg="white",
    insertbackground="white",
    bd=0,
    padx=10,
    pady=10
)
chat_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
chat_box.config(state=tk.DISABLED)

# 🎨 Styles
chat_box.tag_config("user", foreground="#4FC3F7", font=("Segoe UI", 11, "bold"))
chat_box.tag_config("bot", foreground="#A5D6A7")
chat_box.tag_config("typing", foreground="#888888", font=("Segoe UI", 10, "italic"))

# Bottom input
bottom_frame = tk.Frame(window, bg="#1e1e1e")
bottom_frame.pack(fill=tk.X, padx=10, pady=10)

entry = tk.Entry(
    bottom_frame,
    font=("Segoe UI", 13),
    bg="#333",
    fg="white",
    insertbackground="white",
    bd=0
)
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)

send_btn = tk.Button(
    bottom_frame,
    text="Send",
    command=send_message,
    bg="#0e639c",
    fg="white",
    activebackground="#1177bb",
    bd=0,
    padx=15,
    pady=5
)
send_btn.pack(side=tk.RIGHT)

window.bind("<Return>", lambda event: send_message())

entry.focus()
window.mainloop()