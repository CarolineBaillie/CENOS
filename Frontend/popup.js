// js code for extension popup
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById("btn").addEventListener("click", handler);
    document.getElementById("sum").addEventListener("click", summarize);
    document.getElementById("sumNav").addEventListener("click", sumNav);
    document.getElementById("saveNav").addEventListener("click", saveNav);
});

function handler() {
    var cat = document.getElementById("catInput").value;
    chrome.tabs.executeScript( {
        code: "window.getSelection().toString();"
    }, function(selection) {
        let data = selection[0];
        chrome.runtime.sendMessage({title:"post", info: data, cat: cat});
    });  
}

function summarize() {
    chrome.tabs.executeScript( {
        code: "window.getSelection().toString();"
    }, function(selection) {
        let data = selection[0];
        chrome.runtime.sendMessage({title:"sum", info: data});
    });  
}

function sumNav() {
    document.getElementById('saveClass').style.display = 'none';
    document.getElementById('sumClass').style.display = 'block';
}
function saveNav() {
    document.getElementById('saveClass').style.display = 'block';
    document.getElementById('sumClass').style.display = 'none';
}
