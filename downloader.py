import yt_dlp
import os
import sys
from pathlib import Path

class VideoDownloader:
    def __init__(self):
        self.download_path = Path("downloads")
        self.download_path.mkdir(exist_ok=True)
        
    def get_video_info(self, url):
        """Get video information and available formats"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return None
    
    def get_playlist_info(self, url):
        """Get playlist information"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            print(f"Error getting playlist info: {str(e)}")
            return None
    
    def get_available_qualities(self, info, download_type):
        """Extract available qualities based on download type"""
        if not info or 'formats' not in info:
            return []
        
        qualities = []
        
        if download_type in [1, 3]:  # Video with audio
            # Get all video-only formats (YouTube separates video and audio)
            video_formats = [f for f in info['formats'] 
                           if f.get('vcodec') != 'none' and f.get('height')]
            
            # Also get combined formats (for non-YouTube sites)
            combined_formats = [f for f in info['formats'] 
                              if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('height')]
            
            # Group by resolution
            quality_dict = {}
            all_formats = video_formats + combined_formats
            
            for fmt in all_formats:
                height = fmt.get('height')
                fps = fmt.get('fps', 30)
                vcodec = fmt.get('vcodec', '').split('.')[0]  # Get codec name
                
                if height:
                    # Create quality string
                    if fps and fps > 30:
                        quality = f"{height}p{fps}"
                    else:
                        quality = f"{height}p"
                    
                    # Add codec info for better quality selection
                    if vcodec in ['vp9', 'av01']:
                        quality_key = f"{quality}_premium"
                    else:
                        quality_key = f"{quality}_standard"
                    
                    if quality_key not in quality_dict:
                        quality_dict[quality_key] = {
                            'format': fmt,
                            'display': quality,
                            'height': height,
                            'fps': fps or 30,
                            'codec': vcodec
                        }
                    elif fmt.get('tbr', 0) > quality_dict[quality_key]['format'].get('tbr', 0):
                        quality_dict[quality_key] = {
                            'format': fmt,
                            'display': quality,
                            'height': height,
                            'fps': fps or 30,
                            'codec': vcodec
                        }
            
            # Sort by resolution (highest first)
            sorted_qualities = sorted(quality_dict.values(), 
                                    key=lambda x: (x['height'], x['fps']), 
                                    reverse=True)
            
            # Convert to the expected format
            qualities = [(q['display'], q['format']) for q in sorted_qualities]
            
        elif download_type in [2, 4]:  # Audio only
            # Get audio formats
            audio_formats = [f for f in info['formats'] 
                           if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            
            # If no audio-only formats, get audio from combined formats
            if not audio_formats:
                audio_formats = [f for f in info['formats'] 
                               if f.get('acodec') != 'none']
            
            # Group by quality/bitrate
            quality_dict = {}
            for fmt in audio_formats:
                ext = fmt.get('ext', 'unknown')
                abr = fmt.get('abr') or 0  # Handle None values
                acodec = fmt.get('acodec', 'unknown')
                
                # Create a safe numeric value for comparison
                safe_abr = abr if isinstance(abr, (int, float)) and abr > 0 else 0
                
                if safe_abr > 0:
                    quality = f"{ext.upper()} - {safe_abr}kbps ({acodec})"
                else:
                    quality = f"{ext.upper()} ({acodec})"
                
                if quality not in quality_dict:
                    quality_dict[quality] = fmt
                else:
                    # Safe comparison with None handling
                    current_abr = quality_dict[quality].get('abr') or 0
                    current_safe_abr = current_abr if isinstance(current_abr, (int, float)) and current_abr > 0 else 0
                    
                    if safe_abr > current_safe_abr:
                        quality_dict[quality] = fmt
            
            # Sort by bitrate, handling None values safely
            qualities = sorted(quality_dict.items(), 
                             key=lambda x: (x[1].get('abr') or 0) if isinstance(x[1].get('abr'), (int, float)) else 0, 
                             reverse=True)
        
        return qualities
    
    def download_video(self, url, format_id, download_type, output_path=None):
        """Download video with specified format"""
        if not output_path:
            output_path = self.download_path
        
        # Configure download options based on type
        if download_type == 1:  # Video with audio
            # For YouTube and sites with separate streams, merge video and audio
            ydl_opts = {
                'format': f'{format_id}+bestaudio[ext=m4a]/best[height<={self.extract_height_from_format_id(format_id)}]',
                'outtmpl': str(output_path / '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',  # Ensure output is mp4
            }
        elif download_type == 2:  # Audio only
            ydl_opts = {
                'format': f'{format_id}/bestaudio',
                'outtmpl': str(output_path / '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        elif download_type == 3:  # Playlist as videos
            ydl_opts = {
                'format': f'{format_id}+bestaudio[ext=m4a]/best[height<={self.extract_height_from_format_id(format_id)}]',
                'outtmpl': str(output_path / '%(playlist)s/%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
            }
        elif download_type == 4:  # Playlist as audio
            ydl_opts = {
                'format': f'{format_id}/bestaudio',
                'outtmpl': str(output_path / '%(playlist)s/%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            print(f"Download failed: {str(e)}")
            return False
    
    def extract_height_from_format_id(self, format_id):
        """Extract height from format_id for fallback format selection"""
        # This is a helper function to extract resolution for fallback
        try:
            # If format_id is numeric, we need to get the height from the stored info
            # For now, return a reasonable default
            return "1080"
        except:
            return "720"
    
    def is_playlist(self, url):
        """Check if URL is a playlist"""
        playlist_indicators = ['playlist', 'list=', 'album', 'channel']
        return any(indicator in url.lower() for indicator in playlist_indicators)

def display_menu():
    """Display main menu"""
    print("\n" + "="*50)
    print("🎥 ONLINE VIDEO DOWNLOADER")
    print("="*50)
    print("Choose download option:")
    print("1. Video (With Audio)")
    print("2. Only Audio")
    print("3. Playlist as Videos")
    print("4. Playlist as Audio")
    print("0. Exit")
    print("="*50)

def display_qualities(qualities, download_type):
    """Display available qualities"""
    print(f"\n📋 Available qualities:")
    print("-" * 40)
    
    if not qualities:
        print("No suitable formats found!")
        return None
    
    for i, (quality, fmt) in enumerate(qualities, 1):
        if download_type in [1, 3]:  # Video
            codec_info = fmt.get('vcodec', 'unknown').split('.')[0]
            fps = fmt.get('fps')
            fps_info = f" {fps}fps" if fps and fps > 30 else ""
            
            # Show additional quality info
            quality_info = f"{quality}{fps_info}"
            if codec_info in ['vp9', 'av01']:
                quality_info += " (Premium)"
            
            # File size estimate
            filesize = fmt.get('filesize') or fmt.get('filesize_approx')
            if filesize:
                size_mb = filesize / (1024 * 1024)
                size_info = f" (~{size_mb:.1f}MB)"
            else:
                size_info = ""
            
            print(f"{i}. {quality_info}{size_info}")
        else:  # Audio
            print(f"{i}. {quality}")
    
    print("0. Back to main menu")
    print("-" * 40)
    
    while True:
        try:
            choice = int(input("Select quality (number): "))
            if choice == 0:
                return None
            elif 1 <= choice <= len(qualities):
                return qualities[choice - 1][1]['format_id']
            else:
                print("Invalid choice! Please try again.")
        except ValueError:
            print("Please enter a valid number!")

def get_url_input():
    """Get URL input from user"""
    while True:
        url = input("\n🔗 Enter video/playlist URL (or 'back' to return): ").strip()
        if url.lower() == 'back':
            return None
        if url:
            return url
        print("Please enter a valid URL!")

def main():
    downloader = VideoDownloader()
    
    print("🚀 Welcome to Online Video Downloader!")
    print("📁 Downloads will be saved to:", downloader.download_path.absolute())
    
    while True:
        display_menu()
        
        try:
            choice = int(input("Enter your choice: "))
        except ValueError:
            print("❌ Please enter a valid number!")
            continue
        
        if choice == 0:
            print("👋 Thank you for using Video Downloader!")
            sys.exit(0)
        
        if choice not in [1, 2, 3, 4]:
            print("❌ Invalid choice! Please select 1-4 or 0 to exit.")
            continue
        
        # Get URL
        url = get_url_input()
        if not url:
            continue
        
        # Check if it's a playlist for single video options
        if choice in [1, 2] and downloader.is_playlist(url):
            print("⚠️  This appears to be a playlist URL!")
            print("Please use options 3 or 4 for playlists, or provide a single video URL.")
            continue
        
        # Check if it's a single video for playlist options
        if choice in [3, 4] and not downloader.is_playlist(url):
            print("⚠️  This appears to be a single video URL!")
            print("Please use options 1 or 2 for single videos, or provide a playlist URL.")
            continue
        
        print("🔍 Analyzing URL and fetching available formats...")
        
        # Get video/playlist info
        if choice in [3, 4]:  # Playlist
            info = downloader.get_playlist_info(url)
            if not info:
                print("❌ Could not fetch playlist information!")
                continue
                
            print(f"📁 Playlist: {info.get('title', 'Unknown')}")
            print(f"📊 Videos found: {len(info.get('entries', []))}")
            
            # Get info from first video to show available qualities
            if info.get('entries'):
                first_video_url = info['entries'][0]['url']
                sample_info = downloader.get_video_info(first_video_url)
            else:
                print("❌ No videos found in playlist!")
                continue
        else:  # Single video
            info = downloader.get_video_info(url)
            sample_info = info
        
        if not sample_info:
            print("❌ Could not fetch video information!")
            continue
        
        if choice in [1, 2]:
            print(f"🎬 Title: {sample_info.get('title', 'Unknown')}")
            print(f"⏱️  Duration: {sample_info.get('duration', 'Unknown')} seconds")
            print(f"👤 Uploader: {sample_info.get('uploader', 'Unknown')}")
        
        # Get available qualities
        qualities = downloader.get_available_qualities(sample_info, choice)
        
        if not qualities:
            print("❌ No suitable formats found for this content!")
            continue
        
        # Display qualities and get user choice
        format_id = display_qualities(qualities, choice)
        
        if not format_id:
            continue
        
        # Start download
        print(f"\n⬇️  Starting download...")
        print("📁 Download location:", downloader.download_path.absolute())
        
        success = downloader.download_video(url, format_id, choice)
        
        if success:
            print("✅ Download completed successfully!")
        else:
            print("❌ Download failed!")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    # Check if yt-dlp is installed
    try:
        import yt_dlp
    except ImportError:
        print("❌ yt-dlp is not installed!")
        print("Please install it using: pip install yt-dlp")
        sys.exit(1)
    
    # Check if FFmpeg is available (required for merging video/audio)
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  FFmpeg not found!")
        print("FFmpeg is required for high-quality video downloads and audio extraction.")
        print("Please install FFmpeg from: https://ffmpeg.org/download.html")
        print("The program will continue but may have limited functionality.")
        input("Press Enter to continue anyway...")
    
    main()