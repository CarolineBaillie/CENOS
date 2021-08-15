// register events and run code
console.log("working");

chrome.runtime.onMessage.addListener( function(request)
{
    if(request.title=="post") {
        console.log(request.info)
        console.log(request.cat)
        chrome.tabs.query({
            active: true,
            lastFocusedWindow: true
        }, function(tabs) {
            // and use that tab to fill in out title and url
            var tab = tabs[0];
            console.log(tab.url);
            var url = "http://127.0.0.1:5000/";
            fetch(url, {
                method: 'POST',
                mode: 'no-cors',
                body: JSON.stringify({
                    info: request.info, 
                    cat: request.cat,
                    tabUrl: tab.url
                })
            })
        });
    } else if(request.title=="sum"){
        console.log(request.info)
        var url = "http://127.0.0.1:5000/sum";
        fetch(url, {
            mode: 'no-cors'
        })
    }
})
