/**
 * Mobile Touch Behavior Handler
 * Prevents accidental button clicks during scrolling
 * Handles Android back button navigation
 */

(function() {
    'use strict';

    // ===== TOUCH SCROLL vs TAP DETECTION =====

    let touchStartTime = 0;
    let touchStartX = 0;
    let touchStartY = 0;
    let hasMoved = false;
    let isScrolling = false;

    const MOVEMENT_THRESHOLD = 10; // pixels - if moved more than this, it's a scroll
    const TIME_THRESHOLD = 300; // ms - taps should be quick

    // Track touch start
    document.addEventListener('touchstart', function(e) {
        touchStartTime = Date.now();
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        hasMoved = false;
        isScrolling = false;
    }, { passive: true });

    // Track movement during touch
    document.addEventListener('touchmove', function(e) {
        if (!hasMoved) {
            const deltaX = Math.abs(e.touches[0].clientX - touchStartX);
            const deltaY = Math.abs(e.touches[0].clientY - touchStartY);

            // If moved more than threshold, it's a scroll
            if (deltaX > MOVEMENT_THRESHOLD || deltaY > MOVEMENT_THRESHOLD) {
                hasMoved = true;
                isScrolling = true;
            }
        }
    }, { passive: true });

    // Prevent click if it was a scroll
    document.addEventListener('click', function(e) {
        // Check if this was preceded by a scroll gesture
        const timeSinceTouchStart = Date.now() - touchStartTime;

        if (isScrolling && timeSinceTouchStart < 500) {
            // This click happened right after scrolling - block it
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            return false;
        }
    }, { capture: true }); // Use capture to intercept early

    // Reset on touch end
    document.addEventListener('touchend', function(e) {
        // Reset after a short delay to allow click events to process
        setTimeout(function() {
            hasMoved = false;
            isScrolling = false;
        }, 100);
    }, { passive: true });


    // ===== ANDROID BACK BUTTON HANDLING =====

    let lastBackPress = 0;
    const BACK_DOUBLE_TAP_INTERVAL = 2000; // 2 seconds to tap back again to exit

    // Only run on Android devices
    const isAndroid = /Android/i.test(navigator.userAgent);
    const isPWA = window.matchMedia('(display-mode: standalone)').matches ||
                  window.navigator.standalone === true;

    if (isAndroid && isPWA) {
        // Use History API to intercept back button

        // Add a state when the page loads
        if (!window.history.state || !window.history.state.backHandlerInstalled) {
            window.history.pushState({ backHandlerInstalled: true, page: 'current' }, '');
        }

        window.addEventListener('popstate', function(e) {
            const currentPath = window.location.pathname;
            const homePaths = ['/', '/index'];
            const isOnHomePage = homePaths.some(p => currentPath === p || currentPath.startsWith(p));

            if (isOnHomePage) {
                // On home page - handle double-tap to exit
                const now = Date.now();

                if (now - lastBackPress < BACK_DOUBLE_TAP_INTERVAL) {
                    // Second tap within 2 seconds - allow actual back (which will close app)
                    lastBackPress = 0;
                    window.history.back();
                } else {
                    // First tap - show toast and stay on page
                    lastBackPress = now;

                    // Push state again to prevent actual navigation
                    window.history.pushState({ backHandlerInstalled: true, page: 'current' }, '');

                    // Show toast message
                    showBackToast('Tap back again to exit');
                }
            } else {
                // Not on home page - navigate to home instead of browser back
                window.location.href = '/';
            }
        });
    }

    /**
     * Show a temporary toast message at the bottom of the screen
     */
    function showBackToast(message) {
        // Remove existing toast if any
        const existingToast = document.getElementById('back-button-toast');
        if (existingToast) {
            existingToast.remove();
        }

        // Create new toast
        const toast = document.createElement('div');
        toast.id = 'back-button-toast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 12px 24px;
            border-radius: 24px;
            font-size: 14px;
            z-index: 10000;
            animation: fadeInOut 2s ease-in-out;
            pointer-events: none;
        `;

        // Add animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeInOut {
                0% { opacity: 0; transform: translateX(-50%) translateY(20px); }
                10% { opacity: 1; transform: translateX(-50%) translateY(0); }
                90% { opacity: 1; transform: translateX(-50%) translateY(0); }
                100% { opacity: 0; transform: translateX(-50%) translateY(20px); }
            }
        `;
        document.head.appendChild(style);

        document.body.appendChild(toast);

        // Remove after animation
        setTimeout(() => {
            toast.remove();
        }, 2000);
    }


    // ===== ENHANCED TOUCH TARGETS FOR BUTTONS =====

    // Make sure buttons have adequate touch targets on mobile
    if ('ontouchstart' in window) {
        const style = document.createElement('style');
        style.textContent = `
            /* Ensure minimum touch target size */
            @media (pointer: coarse) {
                button, a.btn, .btn {
                    min-height: 44px;
                    min-width: 44px;
                }

                /* Prevent text selection during rapid taps */
                .list-group-item, .card, .btn {
                    -webkit-user-select: none;
                    user-select: none;
                    -webkit-tap-highlight-color: transparent;
                }

                /* Add visual feedback for touch */
                .btn:active {
                    transform: scale(0.98);
                    transition: transform 0.05s;
                }
            }
        `;
        document.head.appendChild(style);
    }

    console.log('Mobile touch handler initialized', {
        isAndroid,
        isPWA,
        backHandlerActive: isAndroid && isPWA
    });
})();
