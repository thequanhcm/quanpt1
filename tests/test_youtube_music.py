# -*- coding: utf-8 -*-
"""Unit tests for YouTube music search and Pi 5 playback dispatch."""

import unittest
from unittest.mock import patch, MagicMock

from quan_ai_brain.media.youtube_music import (
    looks_like_music_request,
    search_youtube_music,
    dispatch_play_music_to_pi5,
    dispatch_stop_music_to_pi5,
)


class TestYouTubeMusic(unittest.TestCase):
    def test_looks_like_music_request_detection(self):
        # Vietnamese music requests
        is_music, query = looks_like_music_request("em bật bài hát Tàu Anh Qua Núi cho anh")
        self.assertTrue(is_music)
        self.assertIn("tàu anh qua núi", query.lower())

        is_music, query = looks_like_music_request("vợ anh muốn nghe bài Tàu Anh Qua Núi em sợ mạng và phát cho anh")
        self.assertTrue(is_music)
        self.assertIn("tàu anh qua núi", query.lower())

        is_music, query = looks_like_music_request("mở bài hát Hãy Trao Cho Anh của Sơn Tùng MTP")
        self.assertTrue(is_music)
        self.assertIn("hãy trao cho anh", query.lower())

        is_music, query = looks_like_music_request("phát nhạc Đất Nước Trọn Niềm Vui")
        self.assertTrue(is_music)
        self.assertIn("đất nước trọn niềm vui", query.lower())

        # Stop requests
        is_music, query = looks_like_music_request("dừng nhạc đi em")
        self.assertTrue(is_music)
        self.assertEqual(query, "STOP")

        is_music, query = looks_like_music_request("tắt nhạc đi em ơi")
        self.assertTrue(is_music)
        self.assertEqual(query, "STOP")

        # Non-music queries
        is_music, query = looks_like_music_request("thời tiết hôm nay thế nào")
        self.assertFalse(is_music)
        self.assertEqual(query, "")

        is_music, query = looks_like_music_request("tình trạng hệ thống DC-COMMAND ra sao")
        self.assertFalse(is_music)
        self.assertEqual(query, "")

    @patch("quan_ai_brain.media.youtube_music.urllib.request.urlopen")
    def test_search_youtube_music_mock(self, mock_urlopen):
        mock_html = """
        <!DOCTYPE html>
        <html>
        <body>
        <script>
        var ytInitialData = {
            "contents": {
                "twoColumnSearchResultsRenderer": {
                    "primaryContents": {
                        "sectionListRenderer": {
                            "contents": [
                                {
                                    "itemSectionRenderer": {
                                        "contents": [
                                            {
                                                "videoRenderer": {
                                                    "videoId": "abc123xyz89",
                                                    "title": {
                                                        "runs": [{"text": "Tàu Anh Qua Núi - NSND Thu Hiền"}]
                                                    },
                                                    "lengthText": {
                                                        "simpleText": "04:35"
                                                    },
                                                    "ownerText": {
                                                        "runs": [{"text": "NSND Thu Hiền Official"}]
                                                    },
                                                    "thumbnail": {
                                                        "thumbnails": [{"url": "https://i.ytimg.com/vi/abc123xyz89/hqdefault.jpg"}]
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        };
        </script>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.read.return_value = mock_html.encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        tracks = search_youtube_music("Tàu Anh Qua Núi", max_results=1)
        self.assertEqual(len(tracks), 1)
        track = tracks[0]
        self.assertEqual(track["video_id"], "abc123xyz89")
        self.assertEqual(track["title"], "Tàu Anh Qua Núi - NSND Thu Hiền")
        self.assertEqual(track["duration"], "04:35")
        self.assertEqual(track["channel"], "NSND Thu Hiền Official")
        self.assertEqual(track["url"], "https://www.youtube.com/watch?v=abc123xyz89")

    @patch("quan_ai_brain.media.youtube_music.urllib.request.urlopen")
    def test_dispatch_play_music_to_pi5_mock(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true, "message": "Playback started", "title": "Tau Anh Qua Nui"}'
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = dispatch_play_music_to_pi5(
            video_id="abc123xyz89",
            title="Tàu Anh Qua Núi",
            url="https://www.youtube.com/watch?v=abc123xyz89",
            edge_ip="192.168.1.21",
            edge_port=8768,
        )
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("title"), "Tàu Anh Qua Núi")

    @patch("quan_ai_brain.media.youtube_music.urllib.request.urlopen")
    def test_dispatch_stop_music_to_pi5_mock(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true, "message": "Playback stopped"}'
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = dispatch_stop_music_to_pi5(
            edge_ip="192.168.1.21",
            edge_port=8768,
        )
        self.assertTrue(res.get("success"))
        self.assertTrue(res.get("data", {}).get("success"))


if __name__ == "__main__":
    unittest.main()
