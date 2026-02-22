/**
 * Popular products carousel for the home page.
 * Shows 5 products at a time on desktop (responsive), auto-scrolls every 5s.
 */
document.addEventListener('DOMContentLoaded', function () {
    const track = document.getElementById('popular-track');
    const viewport = document.getElementById('popular-viewport');
    const prevBtn = document.getElementById('popular-prev');
    const nextBtn = document.getElementById('popular-next');
    const dotsContainer = document.getElementById('popular-dots');

    if (!track || !viewport) return;

    const slides = track.querySelectorAll('.popular-carousel-slide');
    const totalSlides = slides.length;
    if (totalSlides === 0) return;

    let currentPage = 0;
    let autoPlayTimer = null;

    function getVisibleCount() {
        const w = window.innerWidth;
        if (w < 576) return 2;
        if (w < 768) return 3;
        if (w < 992) return 4;
        return 5;
    }

    function getTotalPages() {
        const visible = getVisibleCount();
        return Math.max(1, Math.ceil(totalSlides / visible));
    }

    function buildDots() {
        dotsContainer.innerHTML = '';
        const pages = getTotalPages();
        for (let i = 0; i < pages; i++) {
            const dot = document.createElement('button');
            dot.className = 'popular-carousel-dot' + (i === currentPage ? ' active' : '');
            dot.setAttribute('aria-label', 'Page ' + (i + 1));
            dot.addEventListener('click', function () {
                goToPage(i);
                resetAutoPlay();
            });
            dotsContainer.appendChild(dot);
        }
    }

    function goToPage(page) {
        const pages = getTotalPages();
        const visible = getVisibleCount();
        currentPage = ((page % pages) + pages) % pages;

        const slideEl = slides[0];
        const style = window.getComputedStyle(slideEl);
        const slideWidth = slideEl.offsetWidth;
        const gap = parseFloat(window.getComputedStyle(track).gap) || 16;
        const offset = currentPage * visible * (slideWidth + gap);
        const maxOffset = track.scrollWidth - viewport.offsetWidth;
        track.style.transform = 'translateX(-' + Math.min(offset, Math.max(0, maxOffset)) + 'px)';

        const dots = dotsContainer.querySelectorAll('.popular-carousel-dot');
        dots.forEach(function (d, i) {
            d.classList.toggle('active', i === currentPage);
        });
    }

    function nextPage() {
        goToPage(currentPage + 1);
    }

    function prevPage() {
        goToPage(currentPage - 1);
    }

    function resetAutoPlay() {
        if (autoPlayTimer) clearInterval(autoPlayTimer);
        autoPlayTimer = setInterval(nextPage, 5000);
    }

    prevBtn.addEventListener('click', function () {
        prevPage();
        resetAutoPlay();
    });

    nextBtn.addEventListener('click', function () {
        nextPage();
        resetAutoPlay();
    });

    // Swipe support for mobile
    let touchStartX = 0;
    viewport.addEventListener('touchstart', function (e) {
        touchStartX = e.changedTouches[0].screenX;
    }, {passive: true});
    viewport.addEventListener('touchend', function (e) {
        const diff = touchStartX - e.changedTouches[0].screenX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) nextPage(); else prevPage();
            resetAutoPlay();
        }
    }, {passive: true});

    // Rebuild on resize
    let resizeTimer;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            if (currentPage >= getTotalPages()) currentPage = 0;
            buildDots();
            goToPage(currentPage);
        }, 200);
    });

    buildDots();
    goToPage(0);
    resetAutoPlay();
});
