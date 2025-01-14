console.log("Test js file")

document.querySelectorAll('.ripple-button').forEach(button => {
    button.addEventListener('click', function (event) {
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(button.offsetWidth, button.offsetHeight);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        ripple.className = 'ripple';

        button.appendChild(ripple);

        ripple.addEventListener('animationend', () => ripple.remove());
    });
});

function interrupts(allow) {
    pywebview.api.interruptsPy(allow)
}

function fetchActiveBook() {
    return activeBook
}

function startBookListening(next) {
    //detect single or double click
    const now = new Date().getTime();
    const timeSinceLastClick = now - lastClickTime;
    lastClickTime = now;

    if (timeSinceLastClick < 300) {
        console.log("double click");
        console.log("end reading activity")
        goToScreen("landingScreen")
        stopAudio()
        // Double-click code here
    } else {
        setTimeout(() => {
            if (now === lastClickTime) {
                console.log("single click");
                pywebview.api.startListening(next)
            }
        }, 300);
    }
}

const bookList = document.getElementById("book-list");
let currentIndex = 0;
const audioPlayer = new Audio();
let currentAudio = null;
let booksJS = []

let activeBook = ""

// IntersectionObserver
const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (entry.isIntersecting) {
            const bookName = entry.target.innerText;
            activeBook = bookName
            const audioFile = `books/${bookName}.mp3`;

            // Play the audio for the target book
            if (currentAudio !== audioFile) {
                console.log(`Playing audio for: ${bookName}`);
                currentAudio = audioFile;
                audioPlayer.src = audioFile;
                audioPlayer.play().catch((err) => {
                    console.error("Error playing audio:", err);
                });
            }
        }
    });
}, { root: bookList, threshold: 0.8 });

// Scroll to the next book on click
let targetIndex = 0; // Keep track of the intended target
let lastClickTime = 0;
bookList.addEventListener("click", () => {
    const now = new Date().getTime();
    const timeSinceLastClick = now - lastClickTime;
    lastClickTime = now;

    if (timeSinceLastClick < 300) {
        console.log("double click -> Selected book: " + activeBook);
        goToScreen('interruptChoice')
        // Double-click code here
    } else {
        setTimeout(() => {
            if (now === lastClickTime) {
                console.log("single click -> next book");
                const totalBooks = bookList.children.length;
                const isWrapAround = targetIndex === totalBooks - 1; // Check if we're at the last book

                // Disconnect observer if wrapping around
                if (isWrapAround) {
                    observer.disconnect(); // Temporarily stop observing
                }

                targetIndex = (targetIndex + 1) % booksJS.length; // Move to the next book
                const nextBook = bookList.children[targetIndex];
                nextBook.scrollIntoView({
                    behavior: "smooth",
                    block: "nearest",
                    inline: "start",
                });

                // Reconnect observer after the scroll completes
                setTimeout(() => {
                    if (isWrapAround) {
                        console.log("Reconnecting observer after wrap-around");
                        Array.from(bookList.children).forEach((book) => observer.observe(book));
                    }
                }, 500); // Adjust timeout to match the scroll animation duration
                // Single-click code here
            }
        }, 300);
    }
});

console.log("Run script")
const nextPageBtn = document.querySelector(".nextPageBtn");

if (nextPageBtn) {
    console.log("element here");

    let lastClickTime = 0;

    nextPageBtn.addEventListener('click', event => {
        const now = new Date().getTime();
        const timeSinceLastClick = now - lastClickTime;
        lastClickTime = now;

        if (timeSinceLastClick < 300) {
            console.log("double click");
            endBook()
            // Double-click code here
        } else {
            setTimeout(() => {
                if (now === lastClickTime) {
                    console.log("single click");
                    nextPage()
                    // Single-click code here
                }
            }, 300);
        }
    });
} else {
    console.log("No element found");
}

function testPyCam() {
    pywebview.api.py_cam()
}

function goToScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    })

    document.getElementById(screenId).classList.add('active')
}

function newBook() {
    pywebview.api.newBook()
}

function nextPage() {
    pywebview.api.nextPage()
}

function endBook() {
    pywebview.api.endBook()
}

function fetchBooks() {
    pywebview.api.fetchBooks()
}

function createBookDivs(bookArray) {
    booksJS = bookArray
    const bookList = document.getElementById('book-list');
    bookArray.forEach(book => {
        const div = document.createElement('div');
        div.className = 'book-div';
        div.innerText = book;
        bookList.appendChild(div);
        observer.observe(div);
    });
}

const video = document.getElementById('camera');
const canvas = document.getElementById('photoCanvas');
const captureButton = document.getElementById('captureButton');
const cameraContainer = document.getElementById('camera-container');
const fileInput = document.getElementById('fileInput');

let cameraStream = null;

let audio;

function displayError() {
    const errorContainerEl = document.getElementById("errorContainer")
    errorContainerEl.style.display = 'flex'
    hideLoader()
}

function hideLoader() {
    const loaderEl = document.getElementById("loadercontainer")
    loaderEl.style.display = 'none'
}

function showLoader() {
    const loaderEl = document.getElementById("loadercontainer")
    loaderEl.style.display = 'flex'
}

let currentAudio2 = null;

// Function to play audio
function playAudio(path) {
    stopAudio();  // Stop any currently playing audio

    currentAudio2 = new Audio(path);
    console.log("clicked play audio");
    console.log(path);

    currentAudio2.play().catch(error => {
        console.log('Error playing audio:', error);
    });

    currentAudio2.addEventListener("ended", function () {
        currentAudio2.currentTime = 0;
        console.log("Audio ended");
    });
}

function stopAudio() {
    if (currentAudio2) {
        currentAudio2.pause();
        currentAudio2.currentTime = 0;
        console.log("Audio stopped");
    }
}

// Handle image file selection
let selectedImage = null;
function handleFileSelect(event) {
    selectedImage = event.target.files[0];  // Get the selected file
    if (selectedImage) {
        console.log("File selected: " + selectedImage.name);
    }
}