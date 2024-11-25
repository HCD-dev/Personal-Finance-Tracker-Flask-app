// Sayfa yüklendiğinde bir animasyon efekti
document.addEventListener("DOMContentLoaded", () => {
    const mainContent = document.querySelector("main");
    if (mainContent) {
        mainContent.style.opacity = 0;
        setTimeout(() => {
            mainContent.style.transition = "opacity 0.5s";
            mainContent.style.opacity = 1;
        }, 100);
    }
});


