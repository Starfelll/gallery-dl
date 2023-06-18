# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://bilibili.com/"""

import json

from .common import Extractor, Message
from .. import text, exception


BASE_PATTERN = (r"(?:https?://)?(?:www\.)?(?:bilibili)\.com/")


class BilibiliExtractor(Extractor):
    """Base class for bilibili extractors"""
    category = "bilibili"
    root = "https://www.bilibili.com"
    directory_fmt = ("{category}", "{user[id]}")
    filename_fmt = "{id}_{num}.{extension}"
    archive_fmt = "{id}_{num}"
    cookiedomain = ".bilibili.com"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.api = BilibiliAPI(self)
        self.session.headers.update({
            "Cookie": self.config('token', "")
        })
        pass

    def items(self):
        posts = self.posts()
        metadata = self.metadata()

        for post in posts:
            card = json.loads(post['card'])
            post['card'] = card
            pictures = card['item']['pictures']
            data = {
                'num': 0,
                'raw': post,
                'id': post['desc']['dynamic_id'],
                'user': {
                    'id': post['desc']['uid']
                }
            }
            data.update(metadata)

            yield Message.Directory, data
            for i in range(card['item']['pictures_count']):
                url = pictures[i]['img_src']
                yield Message.Url, url, text.nameext_from_url(url, data)
                data['num'] = data['num'] + 1

    def posts(self):
        """Return an iterable containing all relevant 'posts' objects"""

    def metadata(self):
        """Collect metadata for extractor job"""
        return {}


class BilibiliDynamicExtractor(BilibiliExtractor):
    """Base class for bilibili dynamic extractors"""
    subcategory = "dynamic"
    pattern = BASE_PATTERN + r"opus/([^/?#]+)"

    def __init__(self, match):
        BilibiliExtractor.__init__(self, match)
        self.dynamic_id = match.group(1)

    def posts(self):
        result = self.api.dynamic_detail(self.dynamic_id)['card']
        desc_type = result['desc']['type']
        if desc_type == 2:
            return (result,)
        else:
            self.log.error("Unsupported dynamic type: " + str(desc_type))


class BilibiliAPI:

    def __init__(self, extractor):
        self.extractor = extractor

    def _call(self, endpoint, params=None):
        url = "https://api.vc.bilibili.com" + endpoint

        response = self.extractor.request(url, params=params).json()

        if response['code'] == 0:
            data = response["data"]
            return data
        else:
            raise exception.StopExtraction("API request failed: %s",
                                           response['message'])

    def dynamic_detail(self, dynamic_id):
        return self._call("/dynamic_svr/v1/dynamic_svr/get_dynamic_detail", {
            "dynamic_id": dynamic_id,
        })
