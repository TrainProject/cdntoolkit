# coding=utf-8

import datetime
import json
from typing import no_type_check

from bson.objectid import ObjectId
from orderedattrdict import AttrDict

import util


class AttrJSONEncoder(json.JSONEncoder):
    @no_type_check
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        elif isinstance(obj, (ObjectId, util.FrozenClass)):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


@no_type_check
def attr_json_decoder(d):
    if isinstance(d, list):
        pairs = enumerate(d)
    else:
        pairs = d.items()

    result = []
    for k, v in pairs:
        if isinstance(k, str) and k.find("_id") != -1:
            try:
                v = ObjectId(v)
            except:
                pass
        elif isinstance(v, str):
            try:
                v = datetime.datetime.strptime(v, u'%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                try:
                    v = datetime.datetime.strptime(v, u'%Y-%m-%d').date()
                except ValueError:
                    pass
        elif isinstance(v, (dict, list)):
            v = attr_json_decoder(v)
        result.append((k, v))
    if isinstance(d, list):
        return [x[1] for x in result]
    elif isinstance(d, dict):
        return AttrDict(result)


_default_encoder: json.JSONEncoder = AttrJSONEncoder(
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    indent=None,
    separators=None,
    default=None,
)

_default_decoder: json.JSONDecoder = json.JSONDecoder(
    object_hook=attr_json_decoder,
    object_pairs_hook=None
)


class AttrJson:
    @staticmethod
    def dumps(obj: AttrDict) -> str:
        return _default_encoder.encode(obj)

    @staticmethod
    def loads(s: str) -> AttrDict:
        return _default_decoder.decode(s)
