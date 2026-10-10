from moviepy.editor import TextClip, CompositeVideoClip, ImageClip
from moviepy.config import change_settings
import os

# Specify the full path to ImageMagick's magick.exe
IMAGEMAGICK_BINARY = "F:\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"

# Update MoviePy's settings to use the specified ImageMagick binary
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

# Path to the text file
text_file_path = "F:\\My Code\\reddit stories\\title.txt"

# Directory containing the background images
background_dir = "F:\\My Code\\video intro\\tell_me_thumbnail"

# Output directory for thumbnails
output_dir = "F:\\My Code\\video intro"

# Maximum characters per line
max_chars_per_line = 47

# Interline spacing (in pixels)
interline = 5

def adjust_text(text, max_chars_per_line):
    """
    Adjusts the text to fit within the specified maximum characters per line.
    """
    words = text.split()
    text_lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars_per_line:
            current_line += " " + word
        else:
            text_lines.append(current_line.strip())
            current_line = word

    # Append the last line if it exists
    if current_line:
        text_lines.append(current_line.strip())

    return text_lines

def get_text_position(num_lines, template_name):
    """
    Returns the position of the text and font size based on the number of lines and the template.
    """

    # Set fontsize to always be 40
    fontsize = 39

    # Define horizontal position, vertical position, and font size for each template
    if template_name == "1.jpg":
        horizontal_position = 100
        vertical_position = 100

    elif template_name == "2.jpg":
        horizontal_position = 105
        vertical_position = 100

    elif template_name == "3.jpg":
        horizontal_position = 130
        vertical_position = 150

    elif template_name == "4.jpg":
        horizontal_position = 125
        vertical_position = 130
    
    elif template_name == "5.jpg":
        horizontal_position = 125
        vertical_position = 135

    else:
        horizontal_position = 'center'
        vertical_position = 'center'


    return (horizontal_position, vertical_position, fontsize)

try:
    # Verify the text file path
    if not os.path.exists(text_file_path):
        print(f"Text file not found: {text_file_path}")
    else:
        print(f"Text file found: {text_file_path}")

    # Verify the background directory
    if not os.path.exists(background_dir):
        print(f"Background directory not found: {background_dir}")
    else:
        print(f"Background directory found: {background_dir}")

    # Verify the output directory
    if not os.path.exists(output_dir):
        print(f"Output directory not found: {output_dir}")
        os.makedirs(output_dir)  # Create the output directory if it doesn't exist
        print(f"Created output directory: {output_dir}")
    else:
        print(f"Output directory found: {output_dir}")

    # Read the text from the file
    with open(text_file_path, "r", encoding="utf-8") as file:
        text = file.read().strip()

    # Adjust the text to fit within the specified maximum characters per line
    text_lines = adjust_text(text, max_chars_per_line)
    num_lines = len(text_lines)

    # Choose the appropriate background image based on the number of lines
    template_name = f"{num_lines}.jpg"
    background_image_path = os.path.join(background_dir, template_name)

    if not os.path.exists(background_image_path):
        print(f"Background image not found for {num_lines} lines: {background_image_path}")
    else:
        print(f"Using background image: {background_image_path}")

        # Load the background image
        background = ImageClip(background_image_path)

        # Get the text position and font size based on the template and number of lines
        horizontal_position, vertical_position, fontsize = get_text_position(num_lines, template_name)

        # Create a TextClip with black font color, left-aligned text, and interline spacing
        text_clip = TextClip(
            '\n'.join(text_lines),
            fontsize=fontsize,  # Use the font size returned by get_text_position
            color="black",  # Set font color to black
            font="Arial-Bold",
            align='west',  # Left-align the text
            size=(1080, 1920),  # YouTube Shorts dimensions
            interline=interline  # Set interline spacing
        )

        # Composite the text onto the background
        final_thumbnail = CompositeVideoClip([background, text_clip.set_position((horizontal_position, vertical_position))])

        # Save the thumbnail to the output directory
        output_path = os.path.join(output_dir, f"thumbnail.jpg")

        # Convert the image to RGB mode before saving as JPEG
        final_thumbnail = final_thumbnail.set_mask(None)  # Remove transparency
        final_thumbnail.save_frame(output_path, withmask=False)  # Save without alpha channel

        print(f"Thumbnail saved at: {output_path}")

except Exception as e:
    print(f"Error occurred: {e}")