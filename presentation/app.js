// HyperFrames GSAP Presentation Controller

document.addEventListener("DOMContentLoaded", () => {
  const slides = Array.from(document.querySelectorAll(".slide"));
  const slideIndicator = document.getElementById("slide-indicator");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const fullscreenBtn = document.getElementById("fullscreen-btn");
  const viewport = document.getElementById("presentation-viewport");
  const elapsedTimeEl = document.getElementById("elapsed-time");
  const activeNoteText = document.getElementById("active-note-text");

  let currentIndex = 0;
  let elapsedSeconds = 0;
  let timerInterval = null;

  // Auto-scale presentation viewport to preserve 16:9 1920x1080 ratio
  function autoScaleViewport() {
    const targetWidth = 1920;
    const targetHeight = 1080;
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    const scaleX = windowWidth / targetWidth;
    const scaleY = windowHeight / targetHeight;
    const scale = Math.min(scaleX, scaleY);

    viewport.style.transform = `scale(${scale})`;
  }

  window.addEventListener("resize", autoScaleViewport);
  autoScaleViewport();

  // Timer: elapsed time counter
  function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      elapsedSeconds++;
      const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
      const secs = String(elapsedSeconds % 60).padStart(2, "0");
      elapsedTimeEl.textContent = `${mins}:${secs}`;
    }, 1000);
  }
  startTimer();

  // Update slide display with GSAP transitions
  function showSlide(index) {
    if (index < 0 || index >= slides.length) return;

    const currentSlide = slides[currentIndex];
    const targetSlide = slides[index];

    // GSAP Out animation
    gsap.to(currentSlide, {
      opacity: 0,
      y: -20,
      duration: 0.35,
      ease: "power2.in",
      onComplete: () => {
        currentSlide.classList.remove("active");
        targetSlide.classList.add("active");

        // GSAP In animation
        gsap.fromTo(
          targetSlide,
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" }
        );

        // Animate elements inside the slide
        const cards = targetSlide.querySelectorAll(".card, .stat-card, .metric-box, .gov-card, .step-box");
        if (cards.length > 0) {
          gsap.from(cards, {
            opacity: 0,
            y: 15,
            stagger: 0.08,
            duration: 0.4,
            ease: "back.out(1.2)",
          });
        }

        // Animate bar chart fills if on slide 2
        const barFills = targetSlide.querySelectorAll(".bar-fill");
        if (barFills.length > 0) {
          gsap.from(barFills, {
            width: "0%",
            duration: 0.8,
            ease: "power3.out",
            stagger: 0.1,
          });
        }
      },
    });

    currentIndex = index;
    slideIndicator.textContent = `Slide ${currentIndex + 1} / ${slides.length}`;

    // Update presenter notes
    const noteEl = targetSlide.querySelector(".speaker-notes");
    if (noteEl) {
      activeNoteText.textContent = noteEl.textContent.trim();
    } else {
      activeNoteText.textContent = "";
    }
  }

  // Navigation handlers
  function nextSlide() {
    if (currentIndex < slides.length - 1) {
      showSlide(currentIndex + 1);
    }
  }

  function prevSlide() {
    if (currentIndex > 0) {
      showSlide(currentIndex - 1);
    }
  }

  nextBtn.addEventListener("click", nextSlide);
  prevBtn.addEventListener("click", prevSlide);

  // Fullscreen toggle
  fullscreenBtn.addEventListener("click", () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch((err) => {
        console.error("Fullscreen error:", err);
      });
    } else {
      document.exitFullscreen();
    }
  });

  // Keyboard navigation
  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
      e.preventDefault();
      nextSlide();
    } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
      e.preventDefault();
      prevSlide();
    } else if (e.key.toLowerCase() === "f") {
      fullscreenBtn.click();
    } else if (e.key >= "1" && e.key <= String(slides.length)) {
      showSlide(parseInt(e.key) - 1);
    }
  });

  // Initialize first slide presenter note
  const initialNote = slides[0].querySelector(".speaker-notes");
  if (initialNote) {
    activeNoteText.textContent = initialNote.textContent.trim();
  }
});

