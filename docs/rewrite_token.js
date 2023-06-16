// testing GitGuardian
const newToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2NDg5YjU4OTY0MmM2NDI2YjU3ZjJmODkiLCJraW5nZG9tSWQiOiI2NDg5YjU4OTY0MmM2NDI2YjU3ZjJmODkiLCJ3b3JsZElkIjo4OTY0LCJ2ZXJzaW9uIjo4OTY0LCJhdXRoVHlwZSI6ImVtYUlsIiwicGxhdGZvcm0iOiJ3ZWIiLCJ0aW1lIjoxMTg2ODkwODA1LCJjbGllbnRYb3IiOiIxIiwiaXAiOiIxLjEuMS4xIiwiaWF0IjoxMTg2ODkwODA1LCJleHAiOjE5OTc0OTU2MDUsImlzcyI6Im5vZGdhbWVzLmNvbSIsInN1YiI6InVzZXJJbmZvIn0.OjPUrm_fhfxNrglSAh_5-4B_kCl0lk6JjQ8sbHOP6MU";

// const
const dbName = "/idbfs";
const objName = "FILE_DATA";

// open db
const dbRequest = indexedDB.open(dbName);
dbRequest.onsuccess = (event) => {
  const db = event.target.result;

  // find "PlayerPrefs"
  const keysRequest = db.transaction([objName]).objectStore(objName).getAllKeys();
  keysRequest.onsuccess = () => {
    const playerPrefsKey = keysRequest.result.filter(s => s.includes("PlayerPrefs"))[0];

    // read "PlayerPrefs"
    const readRequest = db.transaction([objName]).objectStore(objName).get(playerPrefsKey);
    readRequest.onsuccess = () => {
      const result = readRequest.result;
      let contents = result.contents;  // Uint8Array
      contents = String.fromCharCode(...contents);  // convert to string

      // find auth_token
      // 0x80 is a long string.
      // Credit: https://discussions.unity.com/t/how-can-i-view-a-webplayer-playerprefs-file/25440/2
      const token = contents.match(/auth_token\x80(.+?)\x07/)[1];
      // The type identifier is followed by an additional 32Bit integer (4-byte little endian) length.
      // After the length int you'll find the actual string.
      // to little endian
      let tokenLength = 0;
      [...token.substring(0, 4)].forEach((each, index) => {
        tokenLength |= parseInt(each.charCodeAt(0)) << (index * 8);
      });
      console.log(`existing auth_token's length: ${tokenLength}`);

      // write new token
      let newTokenLength = newToken.length;
      console.log(`new auth_token's length: ${newTokenLength}`);
      // convert to big endian
      let newTokenLengthBytes = [];
      for (let i = 0; i < 4; i++) {
        newTokenLengthBytes.push(newTokenLength & 0xFF);
        newTokenLength >>= 8;
      }
      newTokenLengthBytes = newTokenLengthBytes.map(each => String.fromCharCode(each)).join("");

      let newPlayerPrefs = contents.replace(token, newTokenLengthBytes + newToken);
      newPlayerPrefs = new Uint8Array([...newPlayerPrefs].map(each => each.charCodeAt(0)));
      result.contents = newPlayerPrefs;

      // write
      db.transaction([objName], "readwrite").objectStore(objName).put(
        result, playerPrefsKey
      );
    }
  };
};
