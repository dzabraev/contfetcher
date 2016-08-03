/*global Components, gBrowser, Cu, XPathResult*/
/*jslint white: true */
/*jslint plusplus: true */
/*jshint esversion: 6 */
    
    var Cc = Components.classes;
    var Ci = Components.interfaces;
    var document = gBrowser.contentDocument;
    var elService = Components.classes["@mozilla.org/eventlistenerservice;1"].getService(Ci.nsIEventListenerService);
    var console = (Cu.import("resource://gre/modules/Console.jsm", {})).console;
    
    //var all =  document.getElementsByTagName("*");

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
    var awayElem = function(elem) {
        //TODO протокол ( for ex. mailto:  ) не уводит со страницы.
        //Надо его добавить.
        if(elem.tagName=='a' && elem.hasAttribute('href')) {
          let href=elem.getAttribute('href');
          if(href[0]=='/' || href.substring(0,5)=='http://')
            return true;
          else
            return false;
          /*
          if( (href=="" || (href.length>0 && href[0]=='#')) ||
              ()
            )
            return false;
          else
            return true;
          */
        }
        else {
          return false;
        }
    };
    
    
    function  ContfetcherPage(document) {
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
      this.document=document;
      this.lastActiveElems=[];
      this.hrefs=new Set();
      this.sawHrefs=new Set(); /*посмотренные гиперссылки*/
      this.last_pushed_button=0; /*id последней нажатой кнопки*/
      this.buttons=[];
      this.enabledButtonCond = function(elem) {
        return elService.hasListenersFor(elem,'click') && !awayElem(elem) && isVisible(elem);
      };
      this.addInt = function(elem,key,n) {
        let newWal=parseInt(elem.getAttribute(key))+n;
        elem.setAttribute(key,newWal);
      };
      this.getElementByCfId = function(cf_id,Except=true) {
        let allNodes = this.document.getElementsByTagName('*');
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
      };
      this.pushButton = function(cf_id) {
        this.layer+=1;
        this.last_pushed_button=cf_id;
        let activeElem=this.getElementByCfId(cf_id);
        let evt = this.document.createEvent("MouseEvents");
        evt.initEvent("click", true, true);
        let ajaxStor=document.getElementById('contfetcherAjaxStorage');
        if(ajaxStor){
          ajaxStor.remove();
        }
        ajaxStor=this.document.createElement('meta');
        ajaxStor.id="contfetcherAjaxStorage";
        ajaxStor.setAttribute('lastid',0);
        document.head.appendChild(ajaxStor);
        activeElem.dispatchEvent(evt);
        this.addInt(activeElem,'contfetcher_nclick',1);
        return true;
      };
      this.checkButtonPushed = function() {
        let ajaxStor=document.getElementById('contfetcherAjaxStorage');
        if(!ajaxStor) {
          console.log('WARNING! function:checkButtonPush reason: element with id=contfetcherAjaxStorage not found');
        }
        let childs=ajaxStor.childNodes;
        let allFin=true;
        for(let k=0;k<childs.length;k++) {
          if(childs[k].nodeType==1 && childs[k].getAttribute('status')!="finished") {
            allFin=false;
            break;
          }
        }
        if(allFin)
          return true;
        else
          return false;
      };
      /*
      this.getElemFeatures = function(elem) {
              var o = {
                link:   undefined,
                tag:    elem.localName,
                text:   elem.text,
                onclick:elem.onclick,
                callbacks:[],
                href:   elem.href,
                color:  elem.style.color
              };

      };
      */
      
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
        childs=elem.childNodes;
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
        return {
          text:elem.text,
          tagName:elem.tagName
        };
      };
      this.enumerateElements = function(cf_id) {
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
        let allNodes = this.document.getElementsByTagName('*');
        let elem;
        for(let i=0;i<allNodes.length;i++) {
          elem=allNodes[i];
          if( !elem.hasAttribute('contfetcher_layer') ) {
            elem.setAttribute('contfetcher_layer',this.layer);
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
              this.log('button found')
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
                this.log('\tthis old button');
                /*эта кнопка уже встречалась ранее*/
                let cfp  =existBf.cf_params;
                buttonId=cfp.cf_id;
                local_nl=      cfp.cf_nl;
                local_newnl=   cfp.cf_newnl;
                local_dry=     cfp.cf_dry;
                local_nclick=  cfp.cf_nclick;
              }
              else {
                this.log('\tthis new button');
                buttonId=this.cnt;
                this.cnt+=1;
                bf.cf_params = {
                  cf_id:   buttonId,
                  cf_nl:     local_nl,
                  cf_newnl:  local_newnl,
                  cf_dry:    local_dry,
                  cf_nclick: local_nclick
                };
                /*Возможно образовалась коллизия по признакам.
                  А именно, elem имеет такие же признаки, как и какая-то
                  другая кнопка, при этом другая кнопка существует сейчас.
                */
                let colliz=this.getElementByCfId(buttonId,false);
                if(colliz)
                  throw "collision: "+JSON.stringify(bf);
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
        activeElem=this.getElementByCfId(cf_id,false);
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
          let pushedButton=undefined;
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
          pushedButton.nl+=nl;
          pushedButton.newnl+=newnl;
        }
        if(newActiveElems.length>0) {
          this.lastActiveElems=newActiveElems;
        }
        return newActiveElems;
      };
      this.getNextButton = function() {
        
      };
      this.log = function() {
        console.log(arguments);
      }
      
      this.enumerateElements(0);
}

    //var curPage=contfetcherPage(document);
/*
    activeElems=[];
    //page.Init(document);
    //page.enumerateElements(0);
    //page.pushButton(5);
    //page.pushButton(9);
    //page.enumerateElements(5);
    //activeElems=page.lastActiveElems;
    
    xplist=[];
    //activeElems=enumerateButtons();
    for(let i=0;i<activeElems.length;i++) {
      //console.log('contfetcher='+activeElems[i].getAttribute('contfetcher'));
      var xp=getXpath(document,activeElems[i]);
      //console.log(xp);
      //console.log(getXpathSimple(document,activeElems[i])+'\n')
      xplist.push(xp)
    }
    

    return xplist;
*/
