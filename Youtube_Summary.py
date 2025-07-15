from pytube import extract
from heapq import nlargest
from youtube_transcript_api import YouTubeTranscriptApi
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from string import punctuation

url = 'https://www.youtube.com/watch?v=EpipswT-LuE&ab_channel=TED'
video_id = extract.video_id(url)
#print(video_id)

transcript = YouTubeTranscriptApi.get_transcript(video_id)
text = ""
for elem in transcript:
    text = text + " " + elem["text"]
text = text.replace("\n", " ")
print(text)