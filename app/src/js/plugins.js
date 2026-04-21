/*
Author: Kemenkum Jabar
*/

//Common plugins
if(document.querySelectorAll("[toast-list]") || document.querySelectorAll('[data-choices]') || document.querySelectorAll("[data-provider]")){
  document.writeln("<script type='text/javascript' src='/static/libs/toastify-js/src/toastify.js'></script>");
  document.writeln("<script type='text/javascript' src='/static/libs/choices.js/public/assets/scripts/choices.min.js'></script>");
  document.writeln("<script type='text/javascript' src='/static/libs/flatpickr/dist/flatpickr.min.js'></script>");
}