```js
// const
let dbName = "/idbfs";
let objName = "FILE_DATA";

// open db
let db;
let request = indexedDB.open(dbName);
request.onsuccess = function (event) {
    db = event.target.result;
};

// find "PlayerPrefs"
let perfs;
let request = db.transaction([objName]).objectStore(objName).getAllKeys();
request.onsuccess = function (event) {
    perfs = request.result.filter(s => s.includes("PlayerPrefs"))[0]
};

// delete it
db.transaction([objName], "readwrite").objectStore(objName).delete(perfs);

// refresh page and see if it's logged out
```
