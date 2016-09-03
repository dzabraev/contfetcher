// ==UserScript==
// @name        jquery_modifier
// @namespace   123
// @description make ajax synchronous everywhere
// @version     1
// @grant       none
// ==/UserScript==

function sleep(milliseconds) {
  var start = new Date().getTime();
  for (var i = 0; i < 1e7; i++) {
    if ((new Date().getTime() - start) > milliseconds){
      break;
    }
  }
}

function defer() {
    if (unsafeWindow.jQuery) {
       replaceJq();
       return;
    }
    else {
        //console.log('wait jquery')
        setTimeout( defer, 1000);
    }
}

function replaceJq() {
  console.log('greaceMonkey: start replacing');
  var origAjax=unsafeWindow.jQuery.ajax;
  var f = function(origAjax) {
   return function(url,options) {
     console.log('url->',JSON.stringify(url),'\noptions->',JSON.stringify(options));
     if(url.dataType == "jsonp") {
       var succ_orig = url.success;       
       var curry_succ = function(orig,id) {
         return function(...args) {
           //unsafeWindow.alert("test");
           console.log('greaceMonkey: curred ajax callback called');
           res=orig(...args);
           console.log('greaceMonkey: curred ajax callback finished');
           elem=document.getElementById('contfetcherAjaxStorage');
           childs=elem.childNodes;
           for (let i=0;i<childs.length;i++) {
             let child=childs[i];
             if(child.nodeType==1 && child.getAttribute('contfetcher_ajax_id')==id){
               child.setAttribute("status","finished");
               console.log('greaseMonkey: ajax jsonp finished, id:',id);
               return res;
             }
           }
           console.log('greaseMonkey(WARNING): element with id=',id,'not found');
           return res;
         }
       }
       elem=document.getElementById('contfetcherAjaxStorage');
       if(!elem) {
         console.log('greaseMonkey: creating Storage');
         elem=document.createElement('meta');
         elem.id="contfetcherAjaxStorage";
         elem.setAttribute('lastid',0);
         document.head.appendChild(elem);
       }
       var lastid=parseInt(elem.getAttribute('lastid'));
       var meta = document.createElement('meta');
       elem.setAttribute("lastid",lastid+1);
       meta.setAttribute("contfetcher_ajax_id",lastid+1)
       meta.setAttribute("status","processing");       
       elem.appendChild(meta);      
       url.success=curry_succ(succ_orig,lastid+1);
       //TODO а если неудача?
       result=origAjax(url,options);
       console.log('greaceMonkey: curryied callback finished');
       return result;
     }
     else {
      url.async=false;
      console.log('greaceMonkey: ajax called');
      return origAjax(url,options);
     }
   };
  };
  unsafeWindow.jQuery.ajax=f(origAjax);
  elem=document.createElement('meta');
  elem.id="contfetcherAjaxCurryd";
  document.head.appendChild(elem);
  console.log('greaceMonkey: $.ajax was replaced');
}                   
                   
window.addEventListener('load', defer,false);

