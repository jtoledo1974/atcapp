// Logout function
// Firebase configuration
// const firebaseConfig = {
//     apiKey: "AIzaSyBGFN_jzYYOYfbQkTxQfjrb_x2_zTBy-Ug",
//     authDomain: "cambios-76578.firebaseapp.com",
//     projectId: "cambios-76578",
//     storageBucket: "cambios-76578.appspot.com",
//     messagingSenderId: "860275865505",
//     appId: "1:860275865505:web:eff419cfc1cfb474d87de0"
// };  


var firebaseConfig = {
    apiKey: "AizaSyBGFN_jzYYOYfbQkTxQfjrb_x2_zTBy-Ug",
    authDomain: "cambios-76578.firebaseapp.com",
    projectId: "cambios-76578",
    storageBucket: "cambios-76578.appspot.com",
    messagingSenderId: "860275865505",
    appId: "1:860275865505:web:eff419cfc1cfb474d87de0"
};
// Initialize Firebase
firebase.initializeApp(firebaseConfig);


// Ensure the script runs after the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function () {
    console.log('Logout script loaded.')
    // Logout function
    function logout() {
        console.log('Logging out...');
        firebase.auth().signOut().then(() => {
            console.log('User signed out.');
            localStorage.clear(); // Clear local storage
            sessionStorage.clear(); // Clear session storage
            clearFirebaseIndexedDB(); // Clear Firebase IndexedDB
            // Redirect to login page or reload to ensure state is cleared
            window.location.href = '/logout';
        }).catch((error) => {
            console.error('Sign out error:', error);
        });
    }

    // Function to clear Firebase's IndexedDB
    function clearFirebaseIndexedDB() {
        if (!window.indexedDB) {
            console.log("This browser doesn't support IndexedDB");
            return;
        }

        var request = indexedDB.deleteDatabase('firebaseLocalStorageDb');
        request.onsuccess = function () {
            console.log("Deleted database successfully");
        };
        request.onerror = function () {
            console.error("Couldn't delete database");
        };
        request.onblocked = function () {
            console.error("Couldn't delete database due to the operation being blocked");
        };
    }

    // Add event listener to logout link
    var logoutLink = document.getElementById('logoutLink');
    if (logoutLink) {
        console.log('Adding event listener to logout link.')
        logoutLink.addEventListener('click', function (event) {
            console.log('Logout link clicked.')
            event.preventDefault();
            logout(); // Call the logout function
        });
        // Prevent the default action 

    }

    // Same with the logout button
    var logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', function (event) {
            event.preventDefault();
            logout(); // Call the logout function
        });
    }

});