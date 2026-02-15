#!/usr/bin/env python3
"""
Production (Render) Credential Setup Script
GUI for converting credential JSON files to Base64 for Render environment variables
"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import base64
import sys


class RenderCredentialSetup:
    """GUI application for converting credentials to Base64"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🔧 LECTOR-NCF - Render Credential Setup")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Current encoded string
        self.encoded_string = ""
        self.current_file_type = ""
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Title
        title_frame = tk.Frame(self.root, bg="#2c3e50", pady=15)
        title_frame.pack(fill=tk.X)
        
        title_label = tk.Label(
            title_frame,
            text="🔧 LECTOR-NCF - Render Credential Setup",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Convert JSON credentials to Base64 for Render deployment",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#ecf0f1"
        )
        subtitle_label.pack()
        
        # Button frame
        button_frame = tk.Frame(self.root, pady=20)
        button_frame.pack()
        
        # Firebase button
        firebase_btn = tk.Button(
            button_frame,
            text="📁 Select Firebase JSON",
            command=lambda: self.select_and_encode("Firebase"),
            font=("Arial", 12),
            bg="#3498db",
            fg="white",
            padx=20,
            pady=10,
            width=20
        )
        firebase_btn.grid(row=0, column=0, padx=10)
        
        # Vision button
        vision_btn = tk.Button(
            button_frame,
            text="📁 Select Vision JSON",
            command=lambda: self.select_and_encode("Vision"),
            font=("Arial", 12),
            bg="#9b59b6",
            fg="white",
            padx=20,
            pady=10,
            width=20
        )
        vision_btn.grid(row=0, column=1, padx=10)
        
        # Result frame
        result_frame = tk.Frame(self.root, padx=20)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        result_label = tk.Label(
            result_frame,
            text="Base64 Encoded String:",
            font=("Arial", 11, "bold")
        )
        result_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Text box for Base64 output
        self.text_box = scrolledtext.ScrolledText(
            result_frame,
            font=("Courier", 9),
            wrap=tk.WORD,
            height=12,
            bg="#f8f9fa",
            relief=tk.SOLID,
            borderwidth=1
        )
        self.text_box.pack(fill=tk.BOTH, expand=True)
        self.text_box.config(state=tk.DISABLED)
        
        # Copy button
        copy_btn = tk.Button(
            result_frame,
            text="📋 Copy to Clipboard",
            command=self.copy_to_clipboard,
            font=("Arial", 11, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=8,
            state=tk.DISABLED
        )
        copy_btn.pack(pady=10)
        self.copy_btn = copy_btn
        
        # Instructions frame
        instructions_frame = tk.Frame(self.root, padx=20, pady=10, bg="#ecf0f1")
        instructions_frame.pack(fill=tk.X, pady=10)
        
        instructions_title = tk.Label(
            instructions_frame,
            text="📝 Instructions for Render:",
            font=("Arial", 11, "bold"),
            bg="#ecf0f1"
        )
        instructions_title.pack(anchor=tk.W)
        
        instructions_text = """
1. Go to: https://dashboard.render.com
2. Select your service: lector-ncf
3. Click: Environment tab
4. Add Environment Variable:
   • Key: FIREBASE_CREDENTIALS_BASE64
   • Value: [paste the Base64 string from above]
5. Also add:
   • FIREBASE_DATABASE_URL=https://facot-app-default-rtdb.firebaseio.com/
   • WHATSAPP_MODE=dual
   • (Add other required variables)
6. Click: Save Changes
7. Wait for automatic redeploy (~2 minutes)
        """
        
        instructions_label = tk.Label(
            instructions_frame,
            text=instructions_text,
            font=("Arial", 9),
            bg="#ecf0f1",
            justify=tk.LEFT,
            anchor=tk.W
        )
        instructions_label.pack(anchor=tk.W, pady=5)
        
        # Bottom buttons
        bottom_frame = tk.Frame(self.root, pady=10)
        bottom_frame.pack()
        
        another_btn = tk.Button(
            bottom_frame,
            text="Select Another File",
            command=self.reset,
            font=("Arial", 10),
            padx=15,
            pady=5
        )
        another_btn.grid(row=0, column=0, padx=5)
        
        done_btn = tk.Button(
            bottom_frame,
            text="Done",
            command=self.root.quit,
            font=("Arial", 10),
            padx=15,
            pady=5
        )
        done_btn.grid(row=0, column=1, padx=5)
    
    def select_and_encode(self, file_type: str):
        """Select a JSON file and encode it to Base64"""
        file_path = filedialog.askopenfilename(
            title=f"Select {file_type} Credentials JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        # Validate JSON
        try:
            with open(file_path, 'r') as f:
                json_content = f.read()
                json.loads(json_content)  # Validate it's valid JSON
        except Exception as e:
            messagebox.showerror(
                "Invalid JSON",
                f"The selected file is not valid JSON:\n\n{str(e)}"
            )
            return
        
        # Encode to Base64
        try:
            encoded = base64.b64encode(json_content.encode()).decode()
            self.encoded_string = encoded
            self.current_file_type = file_type
            
            # Display in text box
            self.text_box.config(state=tk.NORMAL)
            self.text_box.delete(1.0, tk.END)
            self.text_box.insert(1.0, encoded)
            self.text_box.config(state=tk.DISABLED)
            
            # Enable copy button
            self.copy_btn.config(state=tk.NORMAL)
            
            # Show success message in status
            self.show_status(
                f"✅ {file_type} credentials encoded successfully!",
                "green"
            )
            
        except Exception as e:
            messagebox.showerror(
                "Encoding Error",
                f"Failed to encode file:\n\n{str(e)}"
            )
    
    def copy_to_clipboard(self):
        """Copy the Base64 string to clipboard"""
        if not self.encoded_string:
            return
        
        try:
            import pyperclip
            pyperclip.copy(self.encoded_string)
            messagebox.showinfo(
                "Success! ✅",
                f"{self.current_file_type} credentials copied to clipboard!\n\n"
                "Now paste it in Render Environment Variables:\n"
                "Key: FIREBASE_CREDENTIALS_BASE64\n"
                "Value: [paste from clipboard]"
            )
            self.show_status("✅ Copied to clipboard!", "green")
        except ImportError:
            # pyperclip not available, show manual instructions
            messagebox.showwarning(
                "Manual Copy Required",
                "pyperclip not available.\n\n"
                "Please manually select and copy the Base64 text from the box above."
            )
        except Exception as e:
            messagebox.showerror(
                "Clipboard Error",
                f"Failed to copy to clipboard:\n\n{str(e)}\n\n"
                "Please manually select and copy the text from the box above."
            )
    
    def show_status(self, message: str, color: str = "black"):
        """Show status message (currently prints to console, could be extended to GUI)"""
        # For now, just print. Future enhancement: add status label to GUI
        print(message)
    
    def reset(self):
        """Reset the interface for another file"""
        self.encoded_string = ""
        self.current_file_type = ""
        self.text_box.config(state=tk.NORMAL)
        self.text_box.delete(1.0, tk.END)
        self.text_box.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        app = RenderCredentialSetup()
        app.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
