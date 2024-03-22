import json
import os
import platform
import queue
import subprocess
import tkinter as tk
from distutils.version import LooseVersion
from threading import Thread
from tkinter import Entry, Button, Label, Menu, messagebox, ttk, filedialog

import requests


class YoutubeDownloaderGUI:
    def __init__(self, master):
        self.master = master
        master.title("VidLer - Video DownLoader")
        master.iconbitmap("_internal/bin/vidler.ico")


        menubar = Menu(master)
        master.config(menu=menubar)

        self.selected_format = tk.StringVar()
        self.selected_format.set("mp4")
        self.formats = ["mp4", "mp3"]
        self.init_ui()
        self.output_queue = queue.Queue()
        self.download_in_progress = False

        self.url_entry.bind("<FocusIn>", self.clear_progress_label)
        self.dest_entry.bind("<FocusIn>", self.clear_progress_label)
        self.format_dropdown.bind("<<ComboboxSelected>>", self.clear_progress_label)
        self.browse_button.bind("<Button-1>", self.clear_progress_label)
        self.check_yt_dlp_installed()

    def init_ui(self):
        # Create menu bar
        menubar = Menu(self.master)
        self.master.config(menu=menubar)

        # File menu
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Check updates for yt-dlp", command=self.check_for_updates)
        file_menu.add_command(label="Exit", command=self.master.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)

        # help_menu.add_command(label="Update VidLer", command=self.update_vidler)
        menubar.add_cascade(label="Help", menu=help_menu)

        # Initialize UI components
        self.create_input_frame()

        # Make the window not resizable
        self.master.geometry("350x135")
        self.master.resizable(False, False)

    def clear_url_input(self):
        self.url_entry.delete(0, tk.END)
        self.master.focus()

    def clear_progress_label(self, event=None):
        self.progress_label.config(text="")

    def create_input_frame(self):
        # Frame for text and input
        input_frame = ttk.Frame(self.master)
        input_frame.grid(row=0, column=0, pady=10, padx=5)

        # Center the input frame along the x-axis
        self.master.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(0, weight=1)
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_columnconfigure(1, weight=2)  # Adjusted weight for the input bar
        input_frame.grid_columnconfigure(2, weight=1)  # Added column for the button

        # Label for URL entry
        label = Label(input_frame, text="Enter URL:")
        label.grid(row=0, column=0, padx=5, sticky="e")

        # URL Entry
        self.url_entry = Entry(input_frame, width=40)
        self.url_entry.grid(row=0, column=1, padx=5, sticky="ew")

        # Label for destination path
        dest_label = Label(input_frame, text="Dest. Path:")
        dest_label.grid(row=1, column=0, padx=5, sticky="e")

        # Destination Path Entry with default value
        default_dest_path = os.getcwd()
        self.dest_entry = Entry(input_frame, width=30)
        self.dest_entry.insert(0, default_dest_path)  # Set default value
        self.dest_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Browse Button for destination path
        self.browse_button = Button(input_frame, text="Browse", command=self.browse_destination_path)
        self.browse_button.grid(row=2, column=1, padx=5, pady=5, sticky="e")

        self.format_dropdown = ttk.Combobox(input_frame, textvariable=self.selected_format, values=self.formats)
        self.format_dropdown.configure(state='readonly')
        self.format_dropdown.grid(row=2, column=1, padx=1, pady=5, sticky="w")

        # Frame for button
        button_frame = ttk.Frame(input_frame, style="TFrame")
        button_frame.grid(row=3, column=1, pady=5, padx=5, sticky="e")

        # Progress label for download status
        self.progress_label = Label(button_frame, text="")
        self.progress_label.grid(row=0, column=0, pady=5, sticky="e")

        # Single button for download/cancel
        self.download_state = tk.StringVar()
        self.download_state.set("Download")
        self.download_button = Button(button_frame, textvariable=self.download_state, command=self.toggle_download)
        self.download_button.grid(row=0, column=1)

    def browse_destination_path(self):
        dest_path = filedialog.askdirectory()
        if dest_path:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, dest_path)

    def toggle_download(self):
        if not hasattr(self, 'download_thread') or not self.download_thread.is_alive():
            # Disable all input fields and the download button while the download is in progress
            self.disable_inputs()
            self.start_download()
        else:
            # Re-enable all input fields and the download button
            self.enable_inputs()

    def disable_inputs(self):
        # Disable all input fields and the download button
        self.download_button.configure(state=tk.DISABLED)
        self.url_entry.configure(state=tk.DISABLED)
        self.dest_entry.configure(state=tk.DISABLED)
        self.format_dropdown.configure(state=tk.DISABLED)
        self.browse_button.configure(state=tk.DISABLED)

    def enable_inputs(self):
        # Re-enable all input fields and the download button
        self.download_button.configure(state=tk.NORMAL)
        self.url_entry.configure(state=tk.NORMAL)
        self.dest_entry.configure(state=tk.NORMAL)
        self.format_dropdown.configure(state='readonly')
        self.browse_button.configure(state=tk.NORMAL)

    def start_download(self):
        # Show progress label
        self.progress_label.config(text="Downloading...")

        # Run yt-dlp using the determined yt_dlp_path and selected format
        self.download_thread = Thread(target=self.run_yt_dlp, args=(self.url_entry.get(), self.selected_format.get()))
        self.download_thread.start()

    def run_yt_dlp(self, url, selected_format):
        try:
            cmd = [self.get_yt_dlp_path(), url, "-o", os.path.join(self.dest_entry.get(), "%(title)s.%(ext)s")]

            if selected_format == "mp3":
                cmd.extend(["-f", "bestaudio/best", "--extract-audio", "--audio-format", "mp3"])
            elif selected_format == "mp4":
                cmd.extend(["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"])

            startup_info = None
            if platform.system().lower() == 'windows':
                # Create no window on Windows
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creation_flags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                       startupinfo=startup_info, creationflags=creation_flags)

            # Read and send output to the queue line by line
            for line in process.stdout:
                self.output_queue.put(line)

            process.wait()
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
        finally:
            # Enable the download button
            self.toggle_download()

            # Stop progress label
            self.progress_label.config(text="Download Complete")
            self.clear_url_input()

    def show_about(self):
        messagebox.showinfo("About", "Vidler - a video and audio downloader!\nVersion 1.0\n\nhttps://github.com/Apacalpa/ViDLer\n\nMade by Apacalpa")

    def check_yt_dlp_installed(self):
        installed_version = self.get_installed_yt_dlp_version()
        if installed_version == "Not Installed":
            self.prompt_install_yt_dlp()

    def check_for_updates(self):
        try:
            installed_version = self.get_installed_yt_dlp_version()
            latest_version = self.get_latest_yt_dlp_version()

            if installed_version != "Not Installed":
                self.show_update_message(installed_version, latest_version)
            else:
                self.prompt_install_yt_dlp()

        except Exception as e:
            print(f"Error checking for updates: {e}")
            messagebox.showerror("Error", "Error checking for updates.")

    def get_installed_yt_dlp_version(self):
        try:
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            installed_version = subprocess.check_output(["_internal/bin/yt-dlp", "--version"], startupinfo=startup_info, text=True).strip('\n')
            return installed_version
        except FileNotFoundError:
            return "Not Installed"

    def get_latest_yt_dlp_version(self):
        try:
            response = requests.get('https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest')
            release_info = json.loads(response.text)
            latest_version = release_info['tag_name']
            return latest_version
        except Exception as e:
            print(f"Error getting latest version: {e}")
            return None

    def show_update_message(self, installed_version, latest_version):
        if LooseVersion(latest_version) > LooseVersion(installed_version):
            messagebox.showinfo("Check for Updates",
                                f"Installed version: {installed_version}\nNew version available: {latest_version}")
            response = messagebox.askyesno("Install Update", "Do you want to install the latest version?")
            if response == tk.YES:
                self.update_yt_dlp()
        else:
            messagebox.showinfo("Check for Updates",
                                f"Installed version: {installed_version}\nThis is the newest version, all's fine!")

    def prompt_install_yt_dlp(self):
        response = messagebox.askyesno("Install yt-dlp",
                                       "yt-dlp is not installed. Do you want to install the latest version?")
        if response == tk.YES:
            self.update_yt_dlp()
        elif response == tk.NO:
            messagebox.showerror("Error", "yt-dlp is necessary for VidLer to work, please install yt-dlp.")
            quit()

    def update_yt_dlp(self):
        try:
            # Determine the appropriate file extension based on the operating system
            system_platform = platform.system().lower()
            if system_platform == 'windows':
                file_extension = 'exe'
            elif system_platform == 'darwin':
                file_extension = 'macos'
            else:
                file_extension = 'linux'

            # Get the latest version information from GitHub releases
            response = requests.get('https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest')
            release_info = json.loads(response.text)
            latest_version = release_info['tag_name']

            # Find the correct asset for the current operating system
            assets = release_info['assets']
            download_url = None
            for asset in assets:
                if file_extension in asset['name']:
                    download_url = asset['browser_download_url']
                    break

            if download_url:
                # Download the latest binary file
                response = requests.get(download_url)
                binary_data = response.content

                # Write the binary data to a file
                bin_dir = os.path.join(os.getcwd(), '_internal/bin')
                os.makedirs(bin_dir, exist_ok=True)
                binary_filename = os.path.join(bin_dir, 'yt-dlp.exe')
                with open(binary_filename, 'wb') as f:
                    f.write(binary_data)

                messagebox.showinfo("Update yt-dlp", "yt-dlp updated successfully.")
            else:
                messagebox.showerror("Error", "No suitable binary found for your operating system.")
        except Exception as e:
            print(f"Error updating VidLer: {e}")
            messagebox.showerror("Error", "Error updating VidLer.")

    def get_yt_dlp_path(self):
        # Determine the appropriate yt-dlp executable based on the OS
        system_platform = platform.system().lower()
        return '_internal/bin/yt-dlp.exe' if system_platform == 'windows' else '_internal/bin/yt-dlp'


if __name__ == "__main__":
    root = tk.Tk()
    app = YoutubeDownloaderGUI(root)
    root.mainloop()
