# coding=utf8


import re


def compile_regexes(cfg):
  action_cfg=cfg['action_cfg']
  for act in action_cfg:
    selector=act['selector']
    url_regex=re.compile(selector['url_regex'])
    act['selector']['url_regex']=url_regex
