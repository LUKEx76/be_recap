import os
import librosa
from moviepy import ImageClip, CompositeVideoClip, TextClip, concatenate_videoclips, AudioFileClip

SELECTED_YEAR = 2025

# dummy data
DUMMY_MAIN_IMAGE = "data/main_image.jpg"
DUMMY_SECONDARY_IMAGE = "data/secondary_image.jpg"
DUMMY_DATE = "01.01.2025"
DUMMY_LOCATION = "Pavia, Italy"
DUMMY_CAPTION = "what up gay man?"

# https://pixabay.com/music/search/lofi/
DUMMY_TRACK = "data/lofi1.mp3"
DUMMY_TRACK_BPM = 120


def create_bereal_loop():
    print("Analyzing audio track for beats...")
    # 1. Load audio and detect the exact beat timestamps
    # librosa.load returns the audio time series (y) and sampling rate (sr)
    y, sr = librosa.load(DUMMY_TRACK)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    
    # Convert audio frames where beats occur into absolute seconds
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    # We add [0] to grab the number out of the array, and cast to float just to be safe
    print(GENERATE_BEATS_MSG := f"Detected tempo: {float(tempo[0]):.2f} BPM. Found {len(beat_times)} beats.")

    # Target video resolution (Standard 9:16 vertical smartphone format)
    video_width = 1080
    video_height = 1920
    
    video_clips = []
    
    print("Building video frames synced to beats...")
    # 2. Loop through timestamps to create a clip for each beat interval
    # We stop at len(beat_times) - 1 so we can always calculate the distance to the next beat
    for i in range(len(beat_times) - 1):
        duration = beat_times[i+1] - beat_times[i]
        
        # Alternate which image is background vs picture-in-picture on each beat
        if i % 2 == 0:
            bg_path = DUMMY_MAIN_IMAGE
            pip_path = DUMMY_SECONDARY_IMAGE
        else:
            bg_path = DUMMY_SECONDARY_IMAGE
            pip_path = DUMMY_MAIN_IMAGE
            
        # Create Main (Background) Image Clip
        # We explicitly resize it to fill our target canvas dimensions
        bg_clip = (ImageClip(bg_path)
                   .with_duration(duration)
                   .resized(new_size=(video_width, video_height)))
        
        # Create Secondary (Picture-in-Picture) Image Clip
        # Set width to 28% of screen, add a small 30px padding margin from the top-left corner
        pip_width = int(video_width * 0.28)
        pip_clip = (ImageClip(pip_path)
                    .with_duration(duration)
                    .resized(width=pip_width)
                    .with_position((30, 30))) 
        
        # Create Metadata Text Overlays
        # Adjust font, size, and positioning as desired. 
        # Note: TextClip requires ImageMagick installed on your system backend.
        metadata_text = f"{DUMMY_DATE} - {DUMMY_LOCATION}\n\"{DUMMY_CAPTION}\""
        text_clip = (TextClip(text=metadata_text, font_size=40, color='white', method='caption', size=(video_width - 100, None)) # font='Arial-Bold', fontsize=40
                     .with_duration(duration)
                     .with_position(('center', video_height - 250))) # Positioned near the bottom
        
        # Composite layers: Background at bottom, then PIP frame, then Text on top
        frame_composite = CompositeVideoClip([bg_clip, pip_clip, text_clip], size=(video_width, video_height))
        video_clips.append(frame_composite)
        
    print("Concatenating clips and binding audio...")
    # 3. Join all individual clips chronologically
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # 4. Extract the audio track up to the length of our generated animation loop and sync them
    audio_background = AudioFileClip(DUMMY_TRACK).with_duration(final_video.duration)
    final_video = final_video.with_audio(audio_background)
    
    # 5. Compile and render the final MP4 file
    # threads=4 speeds up rendering; libx264/aac ensures high compatibility
    output_filename = "bereal_beat_loop.mp4"
    print(f"Rendering final video to {output_filename}...")
    final_video.write_videofile(
        output_filename, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        threads=4
    )
    print("Video generation complete!")

if __name__ == "__main__":
    # Ensure your data directory exists and has files before running
    if os.path.exists(DUMMY_TRACK):
        create_bereal_loop()
    else:
        print(f"Error: Could not find dummy track asset at '{DUMMY_TRACK}'. Please update paths.")