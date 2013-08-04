import Tkinter as Tk
import lib.pyhk
import Queue

class Overlay():
	def __init__(self, logger):

		hotkey = lib.pyhk.pyhk()
		self.root_widget = Tk.Tk()
		self.root_widget.attributes("-topmost", 1)
		self.root_widget.title("HoI3_statistics overlay")
		self.root_widget.iconbitmap(default='icon.ico')

		self.logger = logger
		self.frame = Tk.Frame(self.root_widget)
		self.frame.pack()

		self.status_label_text = Tk.StringVar()
		self.status_label_text.set("status label")
		self.status_label = Tk.Label(self.frame, textvariable=self.status_label_text)
		self.status_label.pack(side=Tk.BOTTOM)

		self.screenshot_button = Tk.Button(self.frame, text="Screenshot (Ctrl + Alt + s)", command=logger.makeScreenshot)
		self.screenshot_button.pack(side=Tk.LEFT)

		self.quit_button = Tk.Button(self.frame, text="Quit", command=self.frame.quit)
		self.quit_button.pack(side=Tk.LEFT)

		screenshot_shortcut = hotkey.addHotkey(['Ctrl','Alt','S'], logger.makeScreenshot)

	def set_status_text(self, status_string):
		print "setting overlay label"
		self.status_label_text.set(status_string)
		self.root_widget.update()
		print "setted overlay label"

	def start(self):
		self.root_widget.mainloop()

if __name__ == '__main__':
	overlay = Overlay(None)
	overlay.start()

