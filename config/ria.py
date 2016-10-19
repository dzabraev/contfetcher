# coding=utf8
# Для push_only_* символ None означает "Любой"
# Для not_push_*  символ None означает "Пустое множество"
#
#   repeatTraverse =    <True>  обход данной гиперссылки производится при каждом запуске программы
#                       <False> обход гиперссылки производится только один раз
#                       <"day">, <"week">, <"month">, <"year"> обход гиперссылки производится не ранее чем через день, неделю, месяц,год
#                       <Number>    обход не ранее чем через Number секунд.

config={
  'name':'ria',
  'start_url':'https://ria.ru/lenta',
  'prefs':[
    (r'^https://ria.ru/lenta.*',{
      'push_only_id'     :  None,
      'push_only_regex'  :  [r'Загрузить еще'],
      'push_only_class'  :  None,
      'push_only_xpath'  :  None,
      'not_push_id'      :  None,
      'not_push_regex'   :  None,
      'not_push_class'   :  None,
      'not_push_xpath'   :  None,
      'extract_data'     :  None,
      'error_handling'   :  None,
      'repeatTraverse'   :  True,
    }),
    (r'^http://ria.ru/[^/]+/\d+/\d+.html$',{ #это статья. Извлекаем статью, ничего не нажимая.
      'push_only_id':     [], #ничего не нажимаем
      'push_only_regex':  [],
      'push_only_class':  [],
      'push_only_xpath':  [],
      'not_push_id':      None,
      'not_push_regex':   None,
      'not_push_class':   None,
      'not_push_xpath':   None,
      'extract_data':     {
            'readability':  True,
            'extractors':   [],
      },
      'error_handling':   None,
      'repeatTraverse':   False,
    }),
    ('default', {
      'push_only_id':     None,
      'push_only_regex':  None,
      'push_only_class':  None,
      'push_only_xpath':  None,
      'not_push_id':      None,
      'not_push_regex':   None,
      'not_push_class':   None,
      'not_push_xpath':   None,
      'extract_data':     {
            'readability':  True,
            'extractors':   [],
      },
      'error_handling':   None,
      'repeatTraverse':   "month",
    })
  ]
}