/*global Components, browser, Cu, XPathResult*/
/*jslint white: true */
/*jslint plusplus: true */
/*jshint esversion: 6 */

// browser.contentWindow.wrappedJSObject Это window object
// https://wiki.greasespot.net/XPCNativeWrapper

/*
var Cc = Components.classes;
var Ci = Components.interfaces;
var elService = Components.classes["@mozilla.org/eventlistenerservice;1"].getService(Ci.nsIEventListenerService);
var console = (Cu.import("resource://gre/modules/Console.jsm", {})).console;
var { require } = Cu.import("resource://devtools/shared/Loader.jsm", {});
const {EventParsers} = require("devtools/shared/event-parsers");
var ioService = Components.classes["@mozilla.org/network/io-service;1"].getService(Components.interfaces.nsIIOService);
*/



function compareListFeat(f1,f2) {
  if(f1.length==f2.length) {
    for(let i=0,l=f1.length;i<l;i++) {
      if(f1[i]!=f2[i])
        return false;
    }
    return true;
  }
  else {
    return false;
  }
}

function computeListFeat(node) {
  return [node.localName,node.className];
}

function eqNeigh(node) {
  l=node.previousSibling;
  r=node.nextSibling;
  if(l && r) {
    lf=computeListFeat(l);
    rf=computeListFeat(r);
    sf=computeListFeat(node);
    if( compareListFeat(lf,sf) && compareListFeat(sf,rf) )
      return true;
    else
      return false;
  }
  else {
    return false;
  }
}

function computeListLen(node,pattern) {
  let cnt=0,
      childs=node.childNodes,
      ch;
  for(let i=0,l=childs.length;i<l;i++) {
    ch=childs[i];
    if(ch.nodeType!=1)
      continue;
    if(pattern(ch))
      cnt+=1;
  }
  return cnt;
}

var growListThreshold=2;
function isGrowingList(node) {
  if(node.hasAttribute('cfN0') && node.hasAttribute('cfN1')) {
    let n1=parseInt(node.getAttribute('cfN0')),
        n2=parseInt(node.getAttribute('cfN1'));
    n1=n1>0?n1:1;
    if(n2/n1 > growListThreshold)
      return true;
    else
      return false;
  }
  else {
    return false;
  }
}

function pruneList(node,pattern) {
  let childs=node.childNodes,ch,rmCh=[];
  for(let i=0,l=childs.length;i<l;i++) {
    ch=childs[i];
    if(ch.nodeType!=1)
      continue;
    if(pattern(ch))
      rmCh.push(ch);
  }
  for(let i=0,l=rmCh.length;i<l;i++) {
    rmCh[i].remove();
  }
}


function ajax_expected() {
  all=browser.contentDocument.head.getElementsByTagName('script');
  for(let i=0,l=all.length;i<l;i++) {
    script=all[i];
    if(script.hasAttribute('src') && script.getAttribute('src').toLowerCase().search('jquery')!=-1) {
      return true;
    }
  }
  return false;
}

function jquery_defined() {
  let global = browser.contentWindow.wrappedJSObject;
  return global.jQuery!==undefined;
}




function replace_ajax() {
  /*
   * Эта функция заменяет оригинальный(origAjax) jQuery.ajax метод оберткой этого метода.
   * При вызове jQuery.ajax будет вызываться обертка, которая, в свою очередь,
   * будет вызывать origAjax.
   *
   * Каждому вызову $.ajax будет сопоставляться уникальный номер. Данный номер будет
   * записываться в ajax_tasks. После того, как (асинхронный) $.ajax запрос будет
   * выполнен, номер из ajax_tasks будет удаляться. При помощи данного массива будет
   * достигаться синхронность асинхронных ajax запросов.
   * При вызове $.ajax обертка будет извлекать значение глобальной переменной ajax_task,
   * увеличивать его на 1 и записывать в ajax_tasks.
   *
   * Обертка $.ajax во время исполнения будет оборачивать коллбек ajax'a. Таким образом
   * при обработке ответа от сервера, сначала будет выполнена обертка_коллбека, и далее
   * оригинальынй коллбек. Обертка_коллбека по завершении будет извлекать из ajax_tasks
   * свой уникальный номер.
  */
  /*TODO how to implement this wrapping without eval?*/
  browser.contentWindow.wrappedJSObject.eval(`
    let origAjax=window.jQuery.ajax;
    document.cfAsyncTaskErase();
    var f = function(origAjax) {
      /*Обертка для оригинапльного ajax*/
      return function(url,options) {
        if( true /*url.dataType == 'jsonp'*/) {
          let succ_orig = url.success;
          let curry_succ = function(orig,id) {
            /* Обертка для коллбека
              * orig -- Оригинальный callback
              * id   -- уникальный id данног запроса
            */
            return function(...args) {
              let oldVal=document.cfFreezeDoc;
              document.cfFreezeDoc=false;
              res=orig(...args);
              document.cfFreezeDoc=oldVal;
              document.cfAsyncTaskDone(id);
              return res;
            };
          }; /*end of wrapped callback*/
          let uniqId=document.cfAsyncTaskRegister();
          console.log('uniqId', uniqId);
          url.success=curry_succ(succ_orig,uniqId);
          //TODO а если неудача?
          let oldVal=document.cfFreezeDoc;
          document.cfFreezeDoc=false;
          result=origAjax(url ,options);
          document.cfFreezeDoc=oldVal;
          return result;
        }
        else {/*unused*/
          url.async=false;
          let oldVal=document.cfFreezeDoc;
          document.cfFreezeDoc=false;
          let res=origAjax(url,options);
          document.cfFreezeDoc=oldVal;
          return res;
        }
      };
    };
    window.jQuery.ajax=f(origAjax); /*Замена оригинального ajax*/
    window.jQuery.ajax.wrapped=true;
  `);/*end of eval*/
  console.log('CONTFETCHER: ajax replaced');
}

function replace_toggle() {
  browser.contentWindow.wrappedJSObject.eval(`
    let origFun=window.jQuery.fn.toggle;
    let wrap = function(orig) {
      return function(duration,complete) {
        console.log('toggle called');
        this.__contfetcher_toggle__=orig;
        return this.__contfetcher_toggle__(0,complete);
      };
    };
    window.jQuery.fn.toggle=wrap(origFun);
  `);
}

function makeAbsPath(path) {
/*
  if(path[0]=='/' || path[0]=='#' || path[0]=='.' || path[0]=='?')
    return relPathToAbs(path);
  else
    return path;
*/
  /* http://stackoverflow.com/questions/8055763/get-absolute-url-from-relative-url-in-firefox-extension */
  let baseURI = ioService.newURI(browser.contentDocument.location.origin, null, null);
  let absURI  = ioService.newURI(path, null, baseURI);
  return absURI.spec;
}

function getSelfHrefs(type,docum,baseurl,layer) {
  if(!docum) {
    if(browser.contentDocument)
      docum=browser.contentDocument;
    else {
      docum=document;
    }
  }

  if(!docum)
    throw "document is undefined";
  let hrefs=[],
      predicate;
  if(type=="all")
    predicate = elem=>{ 
      return elem.hasAttribute('href') && selfHref(baseurl,elem.getAttribute('href'));
    };
  else if( type=="allVisible" )
    predicate = elem=>{ 
      return elem.hasAttribute('href') && selfHref(baseurl,elem.getAttribute('href')) &&
      visible(elem);
    };
  else if(type=="layer") {
    predicate = elem=>{
      return elem.hasAttribute('href') && selfHref(baseurl,elem.getAttribute('href')) &&
      elem.hasAttribute('contfetcher_layer') &&
      elem.getAttribute('contfetcher_layer')==layer;
    };
  }
  else if(type=="layerVisible") {
    predicate = elem=>{ 
      return elem.hasAttribute('href') && selfHref(baseurl,elem.getAttribute('href')) &&
      visible(elem) &&
      elem.hasAttribute('contfetcher_layer') &&
      elem.getAttribute('contfetcher_layer')==layer;
    };
  }
  else {
    throw "bad arg \"type\", type="+type;
  }


  let allElems=docum.getElementsByTagName('a'), href,idx;
  for(let i=0,l=allElems.length;i<l;i++) {
    let elem=allElems[i];
    if( predicate(elem) ) {
      href=makeAbsPath(elem.getAttribute('href'));
      idx=href.indexOf('#');
      if(idx>0)
        href=href.substring(0,idx);
      hrefs.push(href);
    }
  }
  
  return hrefs;
}

function hasEventListeners(node,type) {
    let parsers = new EventParsers().parsers;
    for (let [,{getListeners}] of parsers) {
      try {
        let infos = getListeners(node);
        for(let i=0,l=infos.length;i<l;i++) {
          if(infos[i].type==type) {
            return true;
          }
        }
      } catch(e) {
        // An object attached to the node looked like a listener but wasn't...
        // do nothing.
      }
    }
    return false;
}


function getEventListeners(node) {
    let parsers = new EventParsers().parsers,
        info=[];
    for (let [,{getListeners}] of parsers) {
      info.push(getListeners(node));
    }
    return info;
}




function enumDebugId(document) {
  if(!document)
    document=browser.contentDocument;
  let allNodes = document.getElementsByTagName('*');
  let elem;
  let cnt=0;
  for(let i=0;i<allNodes.length;i++) {
    elem=allNodes[i];
    if(elem.nodeType != 1) {
      continue;
    }
    //console.log(cnt);
    elem.setAttribute('cf_debug_id',cnt);
    cnt+=1;
  }
}

function getDebugId(id,document) {
  if(!document)
    document=browser.contentDocument;
  let allNodes = document.getElementsByTagName('*');
  let elem;
  for(let i=0;i<allNodes.length;i++) {
    elem=allNodes[i];
    if(elem.nodeType != 1) {
      continue;
    }
    if(elem.hasAttribute('cf_debug_id') && elem.getAttribute('cf_debug_id')==id) {
     return elem;
    }
  }
}

  function getElementByCfId(document,cf_id,Except=true) {
        let allNodes = document.getElementsByTagName('*');
        let elem;
        for(let i=0;i<allNodes.length;i++) {
          elem=allNodes[i];
          if( elem.hasAttribute('contfetcher_id') && elem.getAttribute('contfetcher_id')==cf_id ) {
            return elem;
          }
        }
        if( Except )
          throw "element with given cf_id not found";
        else
          return undefined;
  }



  function getButtonsDescr() {
        let allNodes = browser.contentDocument.getElementsByTagName('*');
        let elem;
        let descrs=[];
        for(let i=0;i<allNodes.length;i++) {
          elem=allNodes[i];
          if( elem.hasAttribute('contfetcher_id') ) {
              let id=elem.getAttribute('contfetcher_id');
              let text=elem.textContent;
              descrs.push([id,text]);
          }
        }
        return descrs;
  }


function hashCode(str) {
  var hash = 0, i, chr, len;
  if (str.length === 0) return hash;
  for (i = 0, len = str.length; i < len; i++) {
    chr   = str.charCodeAt(i);
    hash  = ((hash << 5) - hash) + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
}

function getBase(href) {
  hrefArr=href.split('/');
  if(hrefArr.length<3)
    return [];
  hrefHost=hrefArr[2];
  hrefHostArr=hrefHost.split('.');
  return hrefHostArr;
  //hrefLen=hrefHostArr.length;
  //return [hrefHostArr[hrefLen-2],hrefHostArr[hrefLen-1]];
}

function selfHref(baseurl,href) {
  //console.log(baseurl,href)
  href=makeAbsPath(href);
  b1=getBase(baseurl);
  b2=getBase(href);
  if(b1.length!=b2.length)
    return false;
  for(let i=0,l=b1.length;i<l;i++) {
    if(b1[i]!=b2[i])
      return false;
  }
  return true;
  //return (b1[0]===b2[0]) && (b1[1]===b2[1]) ;
}

function hashPage(document) {
  var H=0,num_hrefs=0,buttonsIds=[];
  allElems=document.getElementsByTagName('*');
  for(let i=0;i<allElems.length;i++) {
    let elem=allElems[i];
    if(elem.nodeType != 1)
      continue;
    if( awayElem(elem) && visible(elem) ) {
      let href = elem.getAttribute('href');
      if( !selfHref(browser.contentDocument.location.origin,href) )
        continue;
      H+=hashCode(href);
      num_hrefs+=1;
    }
    else if (!awayElem(elem) && elem.hasAttribute('contfetcher_id') && visible(elem)) {
      buttonsIds.push(elem.getAttribute('contfetcher_id'));
    }
  }
  buttonsIds.sort( function(a,b) {return a-b; } );
  return [H,num_hrefs,buttonsIds];
}



function getIdActiveElements(document) {
  let ids=[];
  all=document.getElementsByTagName('*');
  for(let i=0,l=all.length;i<l;i++) {
    let elem=all[i];
    if(elem.hasAttribute('contfetcher_id')) {
      ids.push(elem.getAttribute('contfetcher_id'));
    }
  }
  return ids;
}



function deepCompare () {
  var i, l, leftChain, rightChain;

  function compare2Objects (x, y) {
    var p;

    // remember that NaN === NaN returns false
    // and isNaN(undefined) returns true
    if (isNaN(x) && isNaN(y) && typeof x === 'number' && typeof y === 'number') {
         return true;
    }

    // Compare primitives and functions.     
    // Check if both arguments link to the same object.
    // Especially useful on the step where we compare prototypes
    if (x === y) {
        return true;
    }

    // Works in case when functions are created in constructor.
    // Comparing dates is a common scenario. Another built-ins?
    // We can even handle functions passed across iframes
    if ((typeof x === 'function' && typeof y === 'function') ||
       (x instanceof Date && y instanceof Date) ||
       (x instanceof RegExp && y instanceof RegExp) ||
       (x instanceof String && y instanceof String) ||
       (x instanceof Number && y instanceof Number)) {
        return x.toString() === y.toString();
    }

    // At last checking prototypes as good as we can
    if (!(x instanceof Object && y instanceof Object)) {
        return false;
    }

    if (x.isPrototypeOf(y) || y.isPrototypeOf(x)) {
        return false;
    }

    if (x.constructor !== y.constructor) {
        return false;
    }

    if (x.prototype !== y.prototype) {
        return false;
    }

    // Check for infinitive linking loops
    if (leftChain.indexOf(x) > -1 || rightChain.indexOf(y) > -1) {
         return false;
    }

    // Quick checking of one object being a subset of another.
    // todo: cache the structure of arguments[0] for performance
    for (p in y) {
        if (y.hasOwnProperty(p) !== x.hasOwnProperty(p)) {
            return false;
        }
        else if (typeof y[p] !== typeof x[p]) {
            return false;
        }
    }

    for (p in x) {
        if (y.hasOwnProperty(p) !== x.hasOwnProperty(p)) {
            return false;
        }
        else if (typeof y[p] !== typeof x[p]) {
            return false;
        }

        switch (typeof (x[p])) {
            case 'object':
            case 'function':

                leftChain.push(x);
                rightChain.push(y);

                if (!compare2Objects (x[p], y[p])) {
                    return false;
                }

                leftChain.pop();
                rightChain.pop();
                break;

            default:
                if (x[p] !== y[p]) {
                    return false;
                }
                break;
        }
    }

    return true;
  }

  if (arguments.length < 1) {
    return true; //Die silently? Don't know how to handle such case, please help...
    // throw "Need two or more arguments to compare";
  }

  for (i = 1, l = arguments.length; i < l; i++) {

      leftChain = []; //Todo: this can be cached
      rightChain = [];

      if (!compare2Objects(arguments[0], arguments[i])) {
          return false;
      }
  }

  return true;
}

    function sleep(milliseconds) {
      let i;
      var start = new Date().getTime();
      for (i = 0; i < 1e7; i++) {
        if ((new Date().getTime() - start) > milliseconds){
          break;
        }
      }
    }
  
    var numNodes = function(xp,document) {
      let iterator=document.evaluate(xp, document.body, null, XPathResult.ANY_TYPE, null);
      let len=0;
      for(let node=iterator.iterateNext();node;node=iterator.iterateNext()) {
        len++;
      }
      return len;
    };
    
    var getXpath = function(document,elm) {
      var allNodes = document.getElementsByTagName('*'); 
      for (var segs = []; elm && elm.nodeType == 1; elm = elm.parentNode) {
        if (elm.hasAttribute('id')) {
          var uniqueIdCount = 0; 
          for (var n=0;n < allNodes.length;n++) { 
            if (allNodes[n].hasAttribute('id') && allNodes[n].id == elm.id) 
              uniqueIdCount++;
              if (uniqueIdCount > 1) 
                break;
          }
          if ( uniqueIdCount == 1) {
            segs.unshift('id("' + elm.getAttribute('id') + '")'); 
            return segs.join('/');
          }
        }
        let cnt=0;
        if (elm.hasAttribute('class')) {
          for(let sib=elm.parentNode.firstChild;sib;sib=sib.nextSibling) {
            if( sib.nodeType==1 && sib.hasAttribute('class') && sib.getAttribute('class')==elm.getAttribute('class') ) {
              cnt+=1;
            }
          }
          if(cnt==1) {
            segs.unshift(elm.localName.toLowerCase() + '[@class="' + elm.getAttribute('class') + '"]');
          }
        }
        if(cnt!=1) {
          let i=1;
          for (let sib = elm.previousSibling; sib; sib = sib.previousSibling) {
            if (sib.localName == elm.localName) {
              i++;
            }
          }
          segs.unshift(elm.localName.toLowerCase() + '[' + i + ']');
        }
        let xp=segs.join('/');
        xp='//'+xp;
        let len=numNodes(xp,document);
        //console.log('logxp: '+xp+'   ___'+len);
        if (len === 1) {
          return xp;
        }
        else if(len === 0) {
          //console.log("xpath failed");
          throw "xpath failed";
          //return '';
        }
      }
      throw "xpath failed2";
    };
    var getXpathSimple = function(document,elm) {
      for (var segs = []; elm && elm.nodeType == 1; elm = elm.parentNode) {
        let i=1;
        for (let sib = elm.previousSibling; sib; sib = sib.previousSibling) {
          if (sib.localName == elm.localName) {
            i++;
          }
        }
        segs.unshift(elm.localName.toLowerCase() + '[' + i + ']'); 
      }
      return segs.join('/');
    };

    var isVisible = function(elem) {
      //var val=elem.style.display;
      //console.log(val)
      return elem.offsetWidth > 0 && elem.offsetHeight > 0;
      //return elem.style.visibility == 'visible' && elem.style.display != 'none' && elem.style.opacity > 0
    };
    

function on_top(r,element) {
  let x = (r.left + r.right)/2, y = (r.top + r.bottom)/2;
  return browser.contentDocument.elementFromPoint(x, y) === element;
}

function visible(element) {
  var de=browser.contentDocument.documentElement,
      r;
  if (!element || element.nodeType!=1)
    return false;
  if (element.offsetWidth === 0 || element.offsetHeight === 0)
    return false;
  //var height = browser.contentDocument.documentElement.clientHeight,
  let rects = element.getClientRects();
  if (rects.length===0)
    return false;
  r=rects[0];
  //goto first rect
  let x1=de.scrollLeft, y1=de.scrollTop;
  let x = (r.left + r.right)/2 + x1, y = (r.top + r.bottom)/2 + y1;
  de.scrollTo(x,y);
  rects = element.getClientRects(); /*update rect's coordinates*/
  for (var i = 0, l = rects.length; i < l; i++) {
    r = rects[i];
    if (on_top(r,element)) 
      return true;
  }
  childs=element.childNodes;
  for(let i=0,l=childs.length;i<l;i++) {
    if(visible(childs[i]))
      return true;
  }
  return false;
}




    
    var awayElem = function(elem) {
        //TODO протокол ( for ex. mailto:  ) не уводит со страницы.
        //Надо его добавить.
        if(elem.localName=='a' && elem.hasAttribute('href')) {
          let href=elem.getAttribute('href');
          if(href[0]=='/' || href.substring(0,7)=='http://')
            return true;
          else
            return false;
        }
        else {
          return false;
        }
    };
    
    
    function  ContfetcherPage(buttons) {
      /*
        Выделяем все элементы, которые:
          1) имеют на себе click callback
          2) элемент видимый
          3) элемент не уводит со страницы.
        Каждому такому элементу присваиваются аттрибуты
          contfetcher_id: Int -- порядковый номер
          contfetcher_status : enabled|disabled
            если ранее добавленный элемент не удовл. одному из
            свойств 1)-3), то он становится disabled. В противном случае
            он enabled. Если кнопка disabled, то она не нажимается.
          contfetcher_nl: Int -- количество ссылок, которые были
            получены при нажатии на кнопку
          contfetcher_newnl: Int -- кол-во новых ссылкок, которые
            были получены с данной кнопки
          contfetcher_dry: Int -- Характеризует количество нажатий на кнопку
            при которых небыло получено ни одной новой ссылки.
          contfetcher_nclick: Int -- количество нажатий на данную кнопку.
        --------------------------------------------------
          Всем элементам на странице присваиваются следующие аттрибуты:
          contfetcher_layer: Int >=0
            Данное число характеризует, когда был добавлен данный элемент.
            При первичной загрузке странице contfetcher_layer у всех элементов равен
            нулю. При каждом нажатии любой кнопки layer увеличивается на 1. Если при нажатии кнопки
            добавились новые элементы, то их contfetcher_layer равен layer.
          contfetcher_parId: Int -- Если данный элемент появился в результате
            нажатия кнопки с contfetcher_id == ID, то contfetcher_parId равняется ID.
            Если элемент был добавлен при начальной загрузке страницы, то его contfetcher_parId=-1.
      */
      this.cnt=1;
      this.layer=0;
      //browser.contentDocument=document;
      this.lastActiveElems=[];
      this.hrefs=new Set();
      this.sawHrefs=new Set(); /*посмотренные гиперссылки*/
      this.last_pushed_button=0; /*id последней нажатой кнопки*/
      this.buttons=[]; // {.features={.text, .tagName} .cf_params={ .cf_id } }; see computeElemFeatures
      this.enabledButtonCond = function(elem) {
        return elem.nodeType==1 && hasEventListeners(elem,'click') && !awayElem(elem) && visible(elem);
      };
      this.hashPage_lastdata = function(document) {
        var H=0,num_hrefs=0,buttonsIds=[];
        allElems=document.getElementsByTagName('*');
        for(let i=0;i<allElems.length;i++) {
          let elem=allElems[i];
          if(elem.nodeType != 1)
            continue;
          if( elem.hasAttribute('contfetcher_vis') &&
              parseInt(elem.getAttribute('contfetcher_vis'))==this.layer) {
            let href = elem.getAttribute('href');
            if( !selfHref(browser.contentDocument.location.origin,href) )
              continue;
            H+=hashCode(href);
            num_hrefs+=1;
          }
          else if (elem.hasAttribute('contfetcher_id') && visible(elem)) {
            buttonsIds.push(elem.getAttribute('contfetcher_id'));
          }
        }
        buttonsIds.sort( function(a,b) {return a-b; } );
        return [H,num_hrefs,buttonsIds];
      };
      this.addInt = function(elem,key,n) {
        let newWal=parseInt(elem.getAttribute(key))+n;
        elem.setAttribute(key,newWal);
      };
      this.getCurrentButtons = function() {
        let allNodes = browser.contentDocument.getElementsByTagName('*');
        let elem;
        let curBts=[];
        let allBts=this.buttons,allBtsL=allBts.length;
        for(let i=0;i<allNodes.length;i++) {
          elem=allNodes[i];
          if( elem.hasAttribute('contfetcher_id') ) {
            let id=elem.getAttribute('contfetcher_id');
            for(let j=0;j<allBtsL;j++) {
              if(allBts[j].cf_params.cf_id==id) {
                curBts.push(allBts[j]);
                break;
              }
            }
          }
        }
        return curBts;
      };
      this._pushButton = function(cf_id,label) {
        let BUTTON_PUSH_OK="BUTTON_PUSH_OK",
            BUTTON_LOST="BUTTON_LOST";
        this.layer+=1;
        this.last_pushed_button=cf_id;
        let activeElem=getElementByCfId(browser.contentDocument,cf_id,false);
        if(!activeElem) {
          /*похоже, что кнопка пропала*/
          return BUTTON_LOST;
        }
        let evt = browser.contentDocument.createEvent("MouseEvents");
        evt.initEvent("click", true, true);
        activeElem.dispatchEvent(evt);
        this.addInt(activeElem,'contfetcher_nclick',1);
        return BUTTON_PUSH_OK;
      };
      this.pushButton = function(cf_id,label) {
        let oldVal=browser.contentDocument.cfFreezeDoc;
        browser.contentDocument.cfFreezeDoc=false;
        let res=this._pushButton(cf_id,label);
        browser.contentDocument.cfFreezeDoc=oldVal;
        return res;
      };
      this.checkButtonPushed = function(label) {
        let FINISHED=0,NOT_FINISHED=-1;
        if(browser.contentDocument.cfAsyncTaskIsCompleteAll())
          return FINISHED;
        else
          return NOT_FINISHED;
      };
      this.addNewButton = function(x) {
        this.buttons.push(x);
      };
/*
      this.compare_obj = function(x,y) {
        //TODO
        //это сравнение некорректное. Если свойство будет объект, то
        //сравнение будет некорректным.
        for(p in x):
          if( x[p]!=y[p] ) return false;
        for(p in y):
          if( x[p]!=y[p] ) return false;
        return true;
      };
*/
      this.findFeatures = function(bf) {
        let features = this.buttons;
        for(i=0;i<features.length;i++) {
          ebf=features[i];
          f1=ebf.features;
          f2=bf.features;
          if( deepCompare(f1,f2) )
            return ebf;
        }
        return undefined;
      };
      this.computeElemFeatures = function(elem) {
        //childs=elem.childNodes;
        //TODO
        //надо сделать конвертацию DOM поддерева во что-то простое,
        //например строку или объект.
        //каждый узел должен представляться след. сваойствами:
        //  1. tagname
        //  2. text
        //  3. callbacks
        //  4. href
        //  5. background-color
        //  6. font-color
        //  7. font-size
        //  8. font-type
        let txt=elem.textContent.replace(/\n/g," ").replace(/\s+/g," ").replace(/^ */,"").replace(/ *$/,"");
        let feat= {
          text:txt,
          tagName:elem.tagName
        };
        
        if(elem.hasAttribute('class'))
          feat.class=elem.getAttribute('class');
        return feat;
      };
      this.setButtons = function(buttons) {
        this.buttons=buttons;
        let max_cf_id=0;
        for(let i=0,l=buttons.length;i<l;i++) {
          let cf_id = buttons[i].cf_params.cf_id;
          if(cf_id > max_cf_id)
            max_cf_id=cf_id;
        }
        this.cnt=max_cf_id+1;
      };
      this.pruneTree = function() {
        nodes=[browser.contentDocument.body];
        while(nodes.length>0) {
          node=nodes.shift();
          if(isGrowingList(node)) {
            console.log('grown list detected');
            pruneList(node,eqNeigh);
          }
          chs=node.childNodes;
          for(let i=0,l=chs.length;i<l;i++)
            if(chs[i].nodeType==1)
              nodes.push(chs[i]);
        }
      };
      this._enumerateElements = function(cf_id,layer) {
        let activeElem;
        if(cf_id===undefined) {
          cf_id = this.last_pushed_button;
        }
        /*
        if(cf_id>0) {
          activeElem=this.getElementByCfId(cf_id);
        }*/
        let nl=0;
        let newnl=0;
        let newActiveElems=[];
        let allNodes = browser.contentDocument.getElementsByTagName('*');
        let elem;
        if(layer===undefined) {
          layer=this.layer;
        }
        for(let i=0,l=allNodes.length;i<l;i++) {
          elem=allNodes[i];
          let ll=computeListLen(elem,eqNeigh);
          if(this.layer===0)
            elem.setAttribute('cfN0',ll);
          else
            elem.setAttribute('cfN1',ll);
          if( !elem.hasAttribute('contfetcher_layer') ) {
            elem.setAttribute('contfetcher_layer',layer);
            elem.setAttribute('contfetcher_parId',cf_id);
          }
          if( awayElem(elem) ) {
              /*Добавляем новые гиперссылки*/
            nl++;
            let href=elem.getAttribute('href').trim();
            if( !(this.sawHrefs.has(href) || this.hrefs.has(href)) ) {
              newnl++;
              this.hrefs.add(href);
            }
          }
          if ( this.enabledButtonCond(elem) ) { /*this is button*/
            if(!elem.hasAttribute('contfetcher_id')) {
              //this.log('button found');
              let buttonId;
              let local_nl=0;
              let local_newnl=0;
              let local_dry=0;
              let local_nclick=0;
              /*check if elem exists in buttons*/
              let bf = {};
              bf.features = this.computeElemFeatures(elem);
              let existBf= this.findFeatures(bf);
              if( existBf ) {
                //this.log('this old button',JSON.stringify(bf.features));
                //this.log('this old button__',bf.features.text,bf.features.tagName);
                /*эта кнопка уже встречалась ранее*/
                let cfp  =existBf.cf_params;
                buttonId=cfp.cf_id;
                /*Возможно образовалась коллизия по признакам.
                  А именно, elem имеет такие же признаки, как и какая-то
                  другая кнопка, при этом другая кнопка существует сейчас.
                */
                let colliz=getElementByCfId(browser.contentDocument,buttonId,false);
                if(colliz) {
                  //console.log('semms tobe this same buttons');
                  //console.log('collision new',getXpath(browser.contentDocument,elem));
                  //console.log('collision old',getXpath(browser.contentDocument,colliz));
                  continue;
                  //throw "collision: "; //+JSON.stringify(bf);
                }
                local_nl=      cfp.cf_nl;
                local_newnl=   cfp.cf_newnl;
                local_dry=     cfp.cf_dry;
                local_nclick=  cfp.cf_nclick;
              }
              else {
                //this.log('\tthis new button');
                buttonId=this.cnt;
                this.cnt+=1;
                bf.cf_params = {
                  cf_id:   buttonId,
                  cf_nl:     local_nl,
                  cf_newnl:  local_newnl,
                  cf_dry:    local_dry,
                  cf_nclick: local_nclick
                };
                this.buttons.push(bf);
              }
              elem.setAttribute('contfetcher_id',buttonId);
              elem.setAttribute('contfetcher_status',"enabled");
              elem.setAttribute('contfetcher_nl',local_nl);
              elem.setAttribute('contfetcher_newnl',local_newnl);
              elem.setAttribute('contfetcher_dry',local_dry);
              elem.setAttribute('contfetcher_nclick',local_nclick);
              newActiveElems.push(elem);
            }
            else { /*has contfetcher_id*/
              elem.setAttribute('contfetcher_status','enabled');
            }
          }
          else if(elem.hasAttribute('contfetcher_id') && !this.enabledButtonCond(elem)) {
            elem.setAttribute('contfetcher_status','disabled');
          }
        }
        activeElem=getElementByCfId(browser.contentDocument,cf_id,false);
        if(activeElem) {
          if(newnl===0) {
            this.addInt(activeElem,'contfetcher_dry',1);
          }
          else {
            activeElem.setAttribute('contfetcher_dry',0);
          }
          this.addInt(activeElem,'contfetcher_nl',nl);
          this.addInt(activeElem,'contfetcher_newnl',newnl);
        }
        
        if(cf_id>0) {
          let pushedButton;
          for(let i=0;i<this.buttons.length;i++) {
            let button = this.buttons[i];
            if(button.cf_params.cf_id===cf_id) {
              pushedButton=button;
              break;
            }
          }
          if(pushedButton===undefined){
            throw "pushed button not found";
          }
          if(newnl===0) {
            pushedButton.cf_params.cf_dry+=1;
          }
          else {
            pushedButton.cf_params.cf_dry=0;
          }
          //pushedButton.nl+=nl;
          //pushedButton.newnl+=newnl;
        }
        if(newActiveElems.length>0) {
          this.lastActiveElems=newActiveElems;
        }
        return newActiveElems;
      };
      this.enumerateElements = function(cf_id,layer) {
        let oldVal=browser.contentDocument.cfFreezeDoc;
        browser.contentDocument.cfFreezeDoc=false;
        let res=this._enumerateElements(cf_id,layer);
        browser.contentDocument.cfFreezeDoc=oldVal;
        return res;
      };
      this.getNextButton = function() {
        
      };
      this.log = function() {
        console.log(arguments);
      };
      if(buttons)
        this.setButtons(buttons);
      this.enumerateElements(0);
}

/*
function closeTab(idx) {
  gBrowser.curTabs[idx].close()
}
*/


