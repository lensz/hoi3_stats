import overlay
from PIL import Image, ImageOps, ImageFilter
from scipy.misc import imread, imsave
from scipy.ndimage.filters import gaussian_filter
from os.path import splitext
from subprocess import check_call
from PIL import ImageGrab 
import threading
import re
import codecs

class NotCorrectInitializedException(Exception):
	pass

def read_text_file(filepath, mode="r", enc="utf-8"):
    opened = codecs.open(filepath, mode, enc)
    content = opened.read()
    opened.close()
    return content

class LogAction(threading.Thread):

	SCREENSHOT_PATH = "data/screenshot.png"
	GUESS_PATH_BASE = "./tmp_tesseract_file"
	GUESS_PATH = GUESS_PATH_BASE + ".txt"
	PROVINCE_NAMES_PATH = "C:\\Program Files (x86)\\Steam\\SteamApps\\common\\Hearts of Iron 3\\tfh\\mod\\hoi3_stats\\localisation\\province_names.csv"
	LOG_POSITION = (861, 815)  # position of the game log in absolute screen coordinates
	LOG_DIMENSIONS = (437, 139)  # dimensions of the game log

	provinces_list = []

	@staticmethod
	def generate_provinces_list(debug=False):
		print "generating provinces list"
		full_file_lines = read_text_file(LogAction.PROVINCE_NAMES_PATH).split("\n")
		prov_regex = "(?P<generic_name>[^;]*);(?P<english>[^;]*);.*"
		LogAction.provinces_list = [re.match(prov_regex, line).group("english") for line in full_file_lines if not re.match(prov_regex, line) == None]
		if debug:
			print "{} provinces found".format(len(LogAction.provinces_list))
			print "Here are the first entries:"
			for line in LogAction.provinces_list[:11]:
				print "{} : {}".format(type(line), line.encode("utf-8"))

	def __init__(self, overlay, **kwargs):
		print len(LogAction.provinces_list)
		if len(LogAction.provinces_list) == 0:
			print "Please generate provinces list before logging"
			raise NotCorrectInitializedException("Provinces list not generated")

		threading.Thread.__init__(self, **kwargs)
		self.overlay = overlay

	def makeScreenshot(self):
		statustext = "Generate Screenshot at {}".format(self.SCREENSHOT_PATH)
		print statustext
		self.overlay.req_queue.put((overlay.Overlay.REQUEST_STATUS_UPDATE, statustext))

		ImageGrab.grab().save(self.SCREENSHOT_PATH)

		self.preprocess_image(self.SCREENSHOT_PATH)

	def preprocess_image(self, image_path, sigma=.8, img_scale_factor=2.7, scale_mode=Image.ANTIALIAS):
		statustext = "Preprocessing"
		print statustext
		self.overlay.req_queue.put((overlay.Overlay.REQUEST_STATUS_UPDATE, statustext))

		image = Image.open(image_path)
		prepared_path = splitext(image_path)[0] + "-edited.png"

		# crop the gamelog out
		x1 = self.LOG_POSITION[0]
		y1 = self.LOG_POSITION[1]
		x2 = self.LOG_POSITION[0] + self.LOG_DIMENSIONS[0]
		y2 = self.LOG_POSITION[1] + self.LOG_DIMENSIONS[1]
		image = image.crop((x1, y1, x2, y2))

		# invert colors
		image = ImageOps.invert(image)
		# to black and white
		image = image.convert("L")  # to black and white
		threshold = 41
		image = image.point(lambda p: p > threshold and 255)
		#resize
		w, h = image.size
		image = image.resize((int(w * img_scale_factor), int(h * img_scale_factor)), scale_mode)

		#########################
		image.save(prepared_path)
		#########################
		image = imread(prepared_path)
		image = gaussian_filter(image, sigma=sigma)
		#########################
		imsave(prepared_path, image)
		#########################
		image = Image.open(prepared_path)
		image = image.filter(ImageFilter.UnsharpMask)
		#########################
		image.save(prepared_path)
		#########################

		#image = Image.open(prepared_path)
		#image.show()

		self.ocr(prepared_path)

	def ocr(self, image_path):
		statustext = "OCR on {} to {}".format(image_path, self.GUESS_PATH_BASE)
		print statustext
		self.overlay.req_queue.put((overlay.Overlay.REQUEST_STATUS_UPDATE, statustext))

		exe_loc = "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"
		check_call([exe_loc, image_path, self.GUESS_PATH_BASE, "quiet"])

		self.postprocess(self.GUESS_PATH)

	def postprocess(self, guess_path):
		statustext = "Postprocessing"
		print statustext
		self.overlay.req_queue.put((overlay.Overlay.REQUEST_STATUS_UPDATE, statustext))

		guess_text = read_text_file(guess_path)
		self.validation(guess_text)

	def validation(self, postprocessed_text):
		statustext = "Validation"
		print statustext
		self.overlay.req_queue.put((overlay.Overlay.REQUEST_STATUS_UPDATE, statustext))

		def split_text_in_message_lines(multiline_text):
			text = multiline_text
			# split on new line
			lines = text.split("\n")
			# remove empty lines
			#print lines
			lines = [line for line in lines if not line == ""]
			#print lines

			return lines

		def check_for_pattern(line):
			time_regex = "([0-9]|1[0-9]|2[0-3]):([0-5][0-9])"
			day_regex = "([1-9]|1[0-9]|2[0-9]|3[0-1])"
			month_regex = "(January|February|March|April|May|June|July|August|September|October|November|Decemeber)"
			year_regex = "(19(?:2[6-9]|4[0-8]))"
			date_regex = "{}, {} {}, {}".format(time_regex, day_regex, month_regex, year_regex)

			event_patterns = {
							"NAVALBATTLEOVER_LOG" : "We (?P<RESULT>[\w ]*) the (?P<NAME>[\w ]*)."
						}
			found = 0
			for name in event_patterns.keys():
				event_pattern = event_patterns[name]
				pattern = "{} {}".format(date_regex, event_pattern)
				print "searching for pattern {} in {}".format(pattern, line.encode("utf-8"))
				if re.match(pattern, line):
					found += 1
					print "Pattern \"{}\" matched for line: {}".format(name, line.encode("utf-8"))
			print "Found {} pattern matching this line.".format(found)

		lines = split_text_in_message_lines(postprocessed_text)
		for line in lines:
			check_for_pattern(line)

		validated = True
		while not validated:
			# do tests and set validated to true if all of the work properly

			# else: request user intervention 
			self.overlay.req_queue.put((overlay.Overlay.REQUEST_CORRECTION, "This is a dummy text. But correct it!!"))
			self.overlay.wait_for_gui_continue_event.wait()
			postprocessed_text = self.overlay.get_correction_text()

			validated = True

		self.concatenate_logs(postprocessed_text)

	def concatenate_logs(self, validated_text_block):
		statustext = "Concatenate logs"
		print statustext
		self.overlay.req_queue.put((overlay.Overlay.REQUEST_STATUS_UPDATE, statustext))

		print validated_text_block.encode("utf-8")

	def run(self):
		self.makeScreenshot()

if __name__ == '__main__':
	logger = Logger()
	logger.start()