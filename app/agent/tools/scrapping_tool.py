from pytrends.request import TrendReq
import requests
from bs4 import BeautifulSoup
import json
import requests
import math, requests, datetime

YOUTUBE_API_KEY = "AIzaSyBW5w8qRSnNOpyZWmHf3Ot_mbQaukyHdWo"


def google_trend_score(keywords, max_results=5):
    print("🔥 YOUTUBE TREND FUNCTION CALLED", keywords)
    results = {}
    last_week = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat("T")+"Z"

    for keyword in keywords:
        try:
            query = f"{keyword} tamil trailer"

            search_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "regionCode": "IN",
                "publishedAfter": last_week,
                "maxResults": max_results,
                "key": YOUTUBE_API_KEY
            }

            r = requests.get(search_url, params=params)
            data = r.json()

            if "error" in data:
                print("YouTube API error:", data["error"])
                results[keyword] = 0.7
                continue


            video_ids = [i["id"]["videoId"] for i in data.get("items", [])]

            if not video_ids:
                results[keyword] = 0.7
                continue

            stats = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part":"statistics","id":",".join(video_ids),"key": YOUTUBE_API_KEY}
            ).json()

            views = [int(v["statistics"].get("viewCount",0)) for v in stats.get("items",[])]
            avg_views = sum(views)/len(views)

            logv = math.log10(avg_views)
            score = 0.7 + (logv - 5) * 0.6
            score = max(0.7, min(round(score,2),1.3))

            print(keyword,"TN avg views:",avg_views,"score:",score)

            results[keyword] = score

        except Exception as e:
            results[keyword] = 0.7
            print("Error fetching trend for",keyword, ":", e)

    return results

