    var Cc = Components.classes;
    var Ci = Components.interfaces;
    var document = gBrowser.contentDocument;
    var elService = Components.classes["@mozilla.org/eventlistenerservice;1"].getService(Ci.nsIEventListenerService);
    var console = (Cu.import("resource://gre/modules/Console.jsm", {})).console;
    
    //var all =  document.getElementsByTagName("*");
  
    function sleep(milliseconds) {
      var start = new Date().getTime();
      for (var i = 0; i < 1e7; i++) {
        if ((new Date().getTime() - start) > milliseconds){
          break;
        }
      }
    }
  
    var numNodes = function(xp,document) {
      iterator=document.evaluate(xp, document.body, null, XPathResult.ANY_TYPE, null);
      let len=0;
      for(node=iterator.iterateNext();node;node=iterator.iterateNext()) {
        len++;
      }
      return len;
    }
    
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
          };
          if ( uniqueIdCount == 1) {
            segs.unshift('id("' + elm.getAttribute('id') + '")'); 
            return segs.join('/');
          }
        }
        let cnt=0;
        if (elm.hasAttribute('class')) {
          for(sib=elm.parentNode.firstChild;sib;sib=sib.nextSibling) {
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
          for (sib = elm.previousSibling; sib; sib = sib.previousSibling) {
            if (sib.localName == elm.localName) {
              i++;
            }
          }
          segs.unshift(elm.localName.toLowerCase() + '[' + i + ']');
        }
        let xp=segs.join('/');
        xp='//'+xp;
        len=numNodes(xp,document);
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
        for (sib = elm.previousSibling; sib; sib = sib.previousSibling) {
          if (sib.localName == elm.localName) {
            i++;
          }
        }
        segs.unshift(elm.localName.toLowerCase() + '[' + i + ']'); 
      }
      return segs.join('/')
    }

    var isVisible = function(elem) {
      //var val=elem.style.display;
      //console.log(val)
      return elem.offsetWidth > 0 && elem.offsetHeight > 0;
      //return elem.style.visibility == 'visible' && elem.style.display != 'none' && elem.style.opacity > 0
    };
    var awayElem = function(elem) {
        //TODO протокол ( for ex. mailto:  ) не уводит со страницы.
        //Надо его добавить.
        if(elem.tagName='a' && elem.hasAttribute('href')) {
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
    
function ContfetcherPage(document) {
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
        let newWal=parseInt(activeElem.getAttribute(key))+n;
        elem.setAttribute(key,newWal);
      };
      this.getElementByCfId = function(cf_id,Except=true) {
        let allNodes = this.document.getElementsByTagName('*');
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
        activeElem=this.getElementByCfId(cf_id);
        let evt = this.document.createEvent("MouseEvents");
        evt.initEvent("click", true, true);
        ajaxStor=document.getElementById('contfetcherAjaxStorage');
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
        ajaxStor=document.getElementById('contfetcherAjaxStorage');
        if(!ajaxStor) {
          console.log('WARNING! function:checkButtonPush reason: element with id=contfetcherAjaxStorage not found');
        }
        childs=ajaxStor.childNodes;
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
      this.addNewButton = function(x) {
        this.buttons.push(x);
      };
      this.compare_obj = function(x,y) {
        /*TODO
          это сравнение некорректное. Если свойство будет объект, то
          сравнение будет некорректным.
        */
        for(p in x):
          if( x[p]!=y[p] ) return false;
        for(p in y):
          if( x[p]!=y[p] ) return false;
        return true;
      };
      this.findFeatures = function(bf) {
        let features = this.buttons;
        for(i=0;i<features.length;i++) {
          ebf=features[i];
          f1=ebf.features;
          f2=bf.features;
          if( this.compare_obj(f1,f2) )
            return ebf;
        }
        return undefined;
      };
      this.computeElemFeatures = function(elem) {
        childs=elem.childNodes;
        /*TODO
          надо сделать конвертацию DOM поддерева во что-то простое,
          например строку или объект.
          каждый узел должен представляться след. сваойствами:
            1. tagname
            2. text
            3. callbacks
            4. href
            5. background-color
            6. font-color
            7. font-size
            8. font-type
        */
      };
      this.enumerateElements = function(cf_id) {
        if(cf_id>0)
          activeElem=this.getElementByCfId(cf_id);
        if(cf_id==undefined) {
          cf_id = this.last_pushed_button;
        }
        let nl=0;
        let newnl=0;
        let newActiveElems=[];
        let allNodes = this.document.getElementsByTagName('*');
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
              let buttonId=this.cnt;
              let nl=0;
              let newnl=0;
              let dry=0;
              let nclick=0;
              /*check if elem exists in buttons*/
              let bf = {};
              bf['features'] = this.computeElemFeatures(elem);
              existBf= this.findFeatures(bf);
              if( existBf ) {
                /*эта кнопка уже встречалась ранее*/
                let cfp  =exist_bf['contfetcher_params'];
                buttonId=cfp['contfetcher_id'];
                nl=      cfp['contfetcher_nl'];
                newnl=   cfp['contfetcher_newnl'];
                dry=     cfp['contfetcher_dry'];
              }
              else {
                buttonId=this.cnt;
                this.cnt+=1;
                bf['contfetcher_params'] = {
                  contfetcher_id:   buttonId,
                  contfetcher_nl:   nl,
                  contfetcher_newnl:newnl,
                  contfetcher_dry:  dry
                };
                /*Возможно образовалась коллизия по признакам.
                  А именно, elem имеет такие же признаки, как и какая-то
                  другая кнопка, при этом другая кнопка существует сейчас.
                */
                colliz=getElementByCfId(buttonId,false);
                if(colliz)
                  throw "collision: "+JSON.stringify(bf);
                this.buttons.push(bf);
              }
              elem.setAttribute('contfetcher_id',buttonId);
              elem.setAttribute('contfetcher_status',"enabled");
              elem.setAttribute('contfetcher_nl',nl);
              elem.setAttribute('contfetcher_newnl',newnl);
              elem.setAttribute('contfetcher_dry',dry);
              elem.setAttribute('contfetcher_nclick',nclick);
              newActiveElems.push(elem);
            }
            else { /*has contfetcher_id*/
              elem.setAttribute('contfetcher_status','enabled');
            }
          }
          else if(elem.hasAttribute('contfetcher_id') && !enabledButtonCond(elem)) {
            elem.setAttribute('contfetcher_status','disabled');
          }
        }
        if(cf_id > 0) {
          if(newnl==0) {
            this.addInt(activeElem,'contfetcher_dry',1);
          }
          else {
            activeElem.setAttribute('contfetcher_dry',0);
          }
          this.addInt(activeElem,'contfetcher_nl',nl);
          this.addInt(activeElem,'contfetcher_newnl',newnl);
        }
        
        if(newActiveElems.length>0) {
          this.lastActiveElems=newActiveElems;
        }
        return newActiveElems;
      };
      this.getNextButton = function() {
        
      };
      
      this.enumerateElements(0);
};

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