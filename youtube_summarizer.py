from pytube import extract
from heapq import nlargest
from youtube_transcript_api import YouTubeTranscriptApi
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from string import punctuation
import argparse
import sys
import os

# Global variable to track mode
STREAMLIT_MODE = False

def load_nlp_model():
    """Load spacy model - works for both CLI and Streamlit"""
    try:
        return spacy.load('en_core_web_sm')
    except OSError:
        if not STREAMLIT_MODE:
            print("Error: spaCy English model not found.")
            print("Please install it by running: python -m spacy download en_core_web_sm")
        return None

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    try:
        return extract.video_id(url)
    except:
        # Handle different URL formats
        if 'youtube.com/watch?v=' in url:
            return url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[1].split('?')[0]
        else:
            return None

def get_video_transcript(video_id):
    """Get transcript from YouTube video"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = ""
        for elem in transcript:
            text = text + " " + elem["text"]
        text = text.replace("\n", " ")
        return text.strip()
    except Exception as e:
        return None

def summarize_text(text, nlp, summary_length=0.3):
    """Summarize text using spaCy NLP"""
    if not text.strip():
        return "Error: No text to summarize"
    
    document = nlp(text)
    
    # Calculate word frequencies
    word_frequencies = {}
    for word in document:
        word_text = word.text.lower()
        if word_text not in list(STOP_WORDS) and word_text not in punctuation:
            if word.text not in word_frequencies.keys():
                word_frequencies[word.text] = 1
            else:
                word_frequencies[word.text] += 1
    
    if not word_frequencies:
        return "Error: No meaningful words found in text"
    
    # Normalize frequencies
    max_frequency = max(word_frequencies.values())
    for word in word_frequencies.keys():
        word_frequencies[word] = word_frequencies[word] / max_frequency
    
    # Score sentences
    sentence_tokens = [sentence for sentence in document.sents]
    sentence_score = {}
    for sentence in sentence_tokens:
        for word in sentence:
            if word.text.lower() in word_frequencies.keys():
                if sentence not in sentence_score.keys():
                    sentence_score[sentence] = word_frequencies[word.text.lower()]
                else:
                    sentence_score[sentence] += word_frequencies[word.text.lower()]
    
    if not sentence_score:
        return "Error: Could not score sentences"
    
    # Select top sentences
    select_length = max(1, int(len(sentence_tokens) * summary_length))
    summary_sentences = nlargest(select_length, sentence_score, key=sentence_score.get)
    final_summary = [sentence.text for sentence in summary_sentences]
    summary = ' '.join(final_summary)
    
    return summary, sentence_tokens

def summarize_youtube_video_streamlit(url, summary_length=0.3):
    """Main function to summarize YouTube video for Streamlit"""
    try:
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            return "Error: Could not extract video ID from URL"
        
        # Get transcript
        text = get_video_transcript(video_id)
        if not text:
            return "Error: No transcript found for this video"
        
        # Load NLP model with Streamlit caching
        import streamlit as st
        
        @st.cache_resource
        def load_nlp_cached():
            return spacy.load('en_core_web_sm')
        
        nlp = load_nlp_cached()
        result = summarize_text(text, nlp, summary_length)
        
        if isinstance(result, tuple):
            return result[0]  # Return just the summary for streamlit
        else:
            return result
        
    except Exception as e:
        return f"Error: {str(e)}"

# CLI Functions
def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the application header"""
    print("=" * 60)
    print("📺 YOUTUBE VIDEO SUMMARIZER")
    print("=" * 60)
    print()

def print_menu():
    """Print the main menu options"""
    print("Choose an option:")
    print("1. 🔍 Summarize a YouTube video")
    print("2. 📊 Batch summarize multiple videos")
    print("3. 📝 View last summary")
    print("4. ⚙️  Settings")
    print("5. ❓ Help")
    print("6. 🚪 Exit")
    print("-" * 40)

def get_user_choice():
    """Get user menu choice"""
    try:
        choice = input("Enter your choice (1-6): ").strip()
        return choice
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)

def get_summary_length():
    """Get summary length preference from user"""
    print("\nSummary length options:")
    print("1. Very short (10% of original)")
    print("2. Short (20% of original)")
    print("3. Medium (30% of original)")
    print("4. Long (50% of original)")
    print("5. Very long (70% of original)")
    print("6. Custom percentage")
    
    try:
        choice = input("Choose summary length (1-6): ").strip()
        length_map = {
            '1': 0.1,
            '2': 0.2,
            '3': 0.3,
            '4': 0.5,
            '5': 0.7
        }
        
        if choice in length_map:
            return length_map[choice]
        elif choice == '6':
            while True:
                try:
                    custom = float(input("Enter percentage (0.1-1.0): "))
                    if 0.1 <= custom <= 1.0:
                        return custom
                    else:
                        print("Please enter a value between 0.1 and 1.0")
                except ValueError:
                    print("Please enter a valid number")
        else:
            return 0.3  # Default
    except KeyboardInterrupt:
        return 0.3

def summarize_single_video(nlp, last_summary_storage):
    """Handle single video summarization"""
    print("\n" + "="*50)
    print("📺 SINGLE VIDEO SUMMARIZATION")
    print("="*50)
    
    url = input("Enter YouTube URL: ").strip()
    if not url:
        print("❌ No URL provided!")
        input("Press Enter to continue...")
        return
    
    # Extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        print("❌ Invalid YouTube URL!")
        input("Press Enter to continue...")
        return
    
    # Get summary length preference
    summary_length = get_summary_length()
    
    print("\n🔄 Processing video transcript...")
    
    # Get transcript
    text = get_video_transcript(video_id)
    if not text:
        print("❌ No transcript found for this video!")
        print("The video may not have captions/subtitles available.")
        input("Press Enter to continue...")
        return
    
    # Summarize
    result = summarize_text(text, nlp, summary_length)
    
    if isinstance(result, tuple):
        summary, sentences = result
        
        print("\n" + "="*50)
        print("✅ SUMMARY GENERATED SUCCESSFULLY!")
        print("="*50)
        print(f"\n📝 Summary ({len(summary.split())} words):")
        print("-" * 40)
        print(summary)
        print("-" * 40)
        
        # Store last summary
        last_summary_storage['summary'] = summary
        last_summary_storage['url'] = url
        last_summary_storage['word_count'] = len(summary.split())
        last_summary_storage['total_sentences'] = len(sentences)
        
        # Additional options
        print("\nOptions:")
        print("1. Save summary to file")
        print("2. Show all sentences")
        print("3. Return to main menu")
        
        choice = input("Choose an option (1-3): ").strip()
        
        if choice == '1':
            save_summary_to_file(summary, url)
        elif choice == '2':
            show_all_sentences(sentences)
            
    else:
        print(f"❌ Error: {result}")
    
    input("\nPress Enter to continue...")

def save_summary_to_file(summary, url):
    """Save summary to a text file"""
    try:
        filename = f"youtube_summary_{extract_video_id(url)}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"YouTube Video Summary\n")
            f.write(f"URL: {url}\n")
            f.write(f"{'='*50}\n\n")
            f.write(summary)
        
        print(f"✅ Summary saved to: {filename}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")

def show_all_sentences(sentences):
    """Display all sentences from the video"""
    print("\n" + "="*50)
    print("📄 ALL SENTENCES FROM VIDEO")
    print("="*50)
    
    for i, sentence in enumerate(sentences, 1):
        print(f"{i:3d}. {sentence.text.strip()}")
    
    print(f"\n📊 Total sentences: {len(sentences)}")

def batch_summarize(nlp):
    """Handle batch summarization of multiple videos"""
    print("\n" + "="*50)
    print("📊 BATCH SUMMARIZATION")
    print("="*50)
    
    print("Enter YouTube URLs (one per line, empty line to finish):")
    urls = []
    
    while True:
        url = input(f"URL {len(urls)+1}: ").strip()
        if not url:
            break
        urls.append(url)
    
    if not urls:
        print("❌ No URLs provided!")
        input("Press Enter to continue...")
        return
    
    summary_length = get_summary_length()
    
    print(f"\n🔄 Processing {len(urls)} videos...")
    
    results = []
    for i, url in enumerate(urls, 1):
        print(f"Processing video {i}/{len(urls)}...")
        
        video_id = extract_video_id(url)
        if not video_id:
            results.append((url, "Invalid URL"))
            continue
        
        text = get_video_transcript(video_id)
        if not text:
            results.append((url, "No transcript available"))
            continue
        
        result = summarize_text(text, nlp, summary_length)
        if isinstance(result, tuple):
            results.append((url, result[0]))
        else:
            results.append((url, result))
    
    # Display results
    print("\n" + "="*50)
    print("📊 BATCH RESULTS")
    print("="*50)
    
    for i, (url, summary) in enumerate(results, 1):
        print(f"\n{i}. {url}")
        print("-" * 40)
        if summary.startswith("Error:") or summary in ["Invalid URL", "No transcript available"]:
            print(f"❌ {summary}")
        else:
            print(f"✅ Summary ({len(summary.split())} words):")
            print(summary[:200] + "..." if len(summary) > 200 else summary)
    
    # Option to save all results
    choice = input("\nSave all results to file? (y/n): ").strip().lower()
    if choice == 'y':
        try:
            filename = "batch_youtube_summaries.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Batch YouTube Video Summaries\n")
                f.write("="*50 + "\n\n")
                
                for i, (url, summary) in enumerate(results, 1):
                    f.write(f"{i}. {url}\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"{summary}\n\n")
            
            print(f"✅ Results saved to: {filename}")
        except Exception as e:
            print(f"❌ Error saving file: {e}")
    
    input("Press Enter to continue...")

def view_last_summary(last_summary_storage):
    """View the last generated summary"""
    if not last_summary_storage.get('summary'):
        print("\n❌ No previous summary found!")
        input("Press Enter to continue...")
        return
    
    print("\n" + "="*50)
    print("📝 LAST SUMMARY")
    print("="*50)
    
    print(f"URL: {last_summary_storage['url']}")
    print(f"Word count: {last_summary_storage['word_count']}")
    print(f"Total sentences in video: {last_summary_storage['total_sentences']}")
    print("-" * 40)
    print(last_summary_storage['summary'])
    
    input("\nPress Enter to continue...")

def show_settings():
    """Show application settings and info"""
    print("\n" + "="*50)
    print("⚙️ SETTINGS & INFO")
    print("="*50)
    
    # Check spaCy model
    try:
        nlp = spacy.load('en_core_web_sm')
        print("✅ spaCy English model: Loaded")
    except:
        print("❌ spaCy English model: Not found")
        print("   Install with: python -m spacy download en_core_web_sm")
    
    # Check other dependencies
    try:
        import pytube
        print("✅ pytube: Available")
    except:
        print("❌ pytube: Not available")
    
    try:
        import youtube_transcript_api
        print("✅ youtube_transcript_api: Available")
    except:
        print("❌ youtube_transcript_api: Not available")
    
    print(f"\n📋 Current settings:")
    print(f"   Default summary length: 30%")
    print(f"   NLP model: en_core_web_sm")
    
    input("\nPress Enter to continue...")

def show_help():
    """Show help information"""
    print("\n" + "="*50)
    print("❓ HELP")
    print("="*50)
    
    print("""
📺 YouTube Video Summarizer Help

WHAT IT DOES:
This tool extracts transcripts from YouTube videos and creates
intelligent summaries using Natural Language Processing.

HOW TO USE:
1. Choose "Summarize a YouTube video" from the main menu
2. Paste any YouTube video URL
3. Select your preferred summary length
4. Read the generated summary!

SUPPORTED URLs:
- https://www.youtube.com/watch?v=VIDEO_ID
- https://youtu.be/VIDEO_ID
- Any standard YouTube video URL

REQUIREMENTS:
- Video must have captions/subtitles (auto-generated or manual)
- Internet connection for transcript retrieval

FEATURES:
✅ Single video summarization
✅ Batch processing multiple videos
✅ Adjustable summary length
✅ Save summaries to files
✅ View all sentences from video

TROUBLESHOOTING:
- "No transcript found": Video has no captions
- "Invalid URL": Check the YouTube URL format
- "spaCy model error": Run 'python -m spacy download en_core_web_sm'

TIP: Shorter videos may have very brief summaries. Longer
educational content typically produces better summaries.
""")
    
    input("Press Enter to continue...")

def main_cli():
    """Main CLI application loop"""
    global STREAMLIT_MODE
    STREAMLIT_MODE = False
    
    # Check if spaCy model is available
    nlp = load_nlp_model()
    if not nlp:
        return
    
    last_summary_storage = {}
    
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        choice = get_user_choice()
        
        if choice == '1':
            summarize_single_video(nlp, last_summary_storage)
        elif choice == '2':
            batch_summarize(nlp)
        elif choice == '3':
            view_last_summary(last_summary_storage)
        elif choice == '4':
            show_settings()
        elif choice == '5':
            show_help()
        elif choice == '6':
            print("\n👋 Thank you for using YouTube Video Summarizer!")
            break
        else:
            print("\n❌ Invalid choice! Please select 1-6.")
            input("Press Enter to continue...")

# Streamlit UI
def main():
    global STREAMLIT_MODE
    STREAMLIT_MODE = True
    
    import streamlit as st
    
    st.set_page_config(
        page_title="YouTube Video Summarizer",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 YouTube Video Summarizer")
    st.markdown("Enter a YouTube URL to get an AI-powered summary of the video content!")
    
    # Input section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        url = st.text_input(
            "YouTube URL:",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste any YouTube video URL here"
        )
    
    with col2:
        summary_length = st.slider(
            "Summary Length",
            min_value=0.1,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help="0.1 = Very short, 1.0 = Full length"
        )
    
    # Process button
    if st.button("🔍 Summarize Video", type="primary"):
        if url:
            with st.spinner("Processing video transcript..."):
                summary = summarize_youtube_video_streamlit(url, summary_length)
                
                if summary.startswith("Error:"):
                    st.error(summary)
                else:
                    st.success("Summary generated successfully!")
                    st.subheader("📝 Video Summary")
                    st.text_area(
                        "Summary:",
                        summary,
                        height=300,
                        label_visibility="collapsed"
                    )
                    
                    # Additional info
                    word_count = len(summary.split())
                    st.info(f"Summary contains {word_count} words")
        else:
            st.warning("Please enter a YouTube URL first!")
    
    # Instructions
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. **Copy a YouTube URL** - Any standard YouTube video URL
        2. **Adjust summary length** - Use the slider to control how detailed the summary should be
        3. **Click Summarize** - The app will extract the transcript and create a summary
        4. **Read your summary** - The most important sentences will be highlighted
        
        **Note:** This tool only works with videos that have transcripts/captions available.
        
        **CLI Mode:** Run `python script.py --cli` for command-line interface
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("Built with Streamlit • Powered by spaCy NLP")

if __name__ == "__main__":
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='YouTube Video Summarizer')
    parser.add_argument('--cli', action='store_true', 
                       help='Run in command-line interface mode')
    args = parser.parse_args()
    
    if args.cli:
        main_cli()
    else:
        main()