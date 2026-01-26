/**
 * Fast Actions - Optimistic UI Updates for Orbis
 * Updates UI immediately, syncs with server in background
 */

(function() {
    'use strict';

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    // Track pending vs completed counts for progress bar updates
    let pendingCount = 0;
    let completedCount = 0;
    let totalCount = 0;

    function initCounts() {
        const progressText = document.querySelector('.progress + small.text-muted');
        if (progressText) {
            const match = progressText.textContent.match(/(\d+)\/(\d+)/);
            if (match) {
                completedCount = parseInt(match[1]);
                totalCount = parseInt(match[2]);
                pendingCount = totalCount - completedCount;
            }
        }
    }

    function updateProgressBar() {
        const progressBar = document.querySelector('.progress-bar.bg-success');
        const progressText = document.querySelector('.progress + small.text-muted');

        if (progressBar && progressText) {
            const pct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
            progressBar.style.width = pct + '%';
            progressBar.setAttribute('aria-valuenow', pct);
            progressBar.textContent = pct + '%';
            progressText.textContent = `${completedCount}/${totalCount} completed`;

            // Check for 100% completion
            if (pct === 100 && !document.querySelector('.alert-success.alert-lg')) {
                showCompletionCelebration();
            }
        }
    }

    function showCompletionCelebration() {
        const card = document.querySelector('.card');
        if (card && !document.getElementById('completionAlert')) {
            const alert = document.createElement('div');
            alert.id = 'completionAlert';
            alert.className = 'alert alert-success alert-lg py-5 text-center mb-4';
            alert.innerHTML = `
                <h2 class="mb-3">
                    <i class="bi bi-check-circle" style="font-size: 3rem;"></i>
                </h2>
                <h3 class="mb-0">Great job! Free time now!</h3>
            `;
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s';
            card.parentNode.insertBefore(alert, card);
            requestAnimationFrame(() => alert.style.opacity = '1');
        }
    }

    function hideCompletionCelebration() {
        const alert = document.getElementById('completionAlert');
        if (alert) {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }
    }

    /**
     * Toggle item completion with optimistic UI update
     */
    function toggleItem(listItem, btn, url, extraData = {}) {
        const isCompleted = btn.classList.contains('btn-success') ||
                           btn.classList.contains('btn-outline-secondary');
        const title = listItem.querySelector('h5');
        const icon = btn.querySelector('i');

        // Optimistic UI update
        if (isCompleted) {
            // Mark as pending (undo completion)
            btn.classList.remove('btn-success', 'btn-outline-secondary');
            // Restore original priority class or default
            const originalClass = btn.dataset.originalClass || 'btn-outline-success';
            btn.className = btn.className.replace(/btn-\S+/g, '').trim();
            btn.classList.add('btn', originalClass);
            icon.className = 'bi bi-circle';
            if (title) {
                title.classList.remove('text-decoration-line-through', 'text-muted');
            }
            completedCount--;
            hideCompletionCelebration();
        } else {
            // Save original class for potential undo
            const classes = Array.from(btn.classList).find(c => c.startsWith('btn-outline-'));
            btn.dataset.originalClass = classes || 'btn-outline-success';
            // Mark as completed
            btn.classList.remove('btn-outline-success', 'btn-outline-warning', 'btn-outline-danger', 'btn-outline-orange');
            btn.classList.add('btn-success');
            icon.className = 'bi bi-check-circle-fill';
            if (title) {
                title.classList.add('text-decoration-line-through', 'text-muted');
            }
            completedCount++;
        }

        updateProgressBar();

        // Background sync
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(extraData)
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                // Revert on failure
                console.error('Toggle failed:', data.error);
                revertToggle(listItem, btn, !isCompleted);
            } else if (data.streak_count !== undefined) {
                // Update streak badge if present
                const streakBadge = listItem.querySelector('.streak-badge');
                if (streakBadge) {
                    if (data.streak_count > 0) {
                        streakBadge.innerHTML = `<i class="bi bi-fire"></i> ${data.streak_count}`;
                    } else {
                        streakBadge.innerHTML = '';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Toggle error:', error);
            revertToggle(listItem, btn, !isCompleted);
        });
    }

    function revertToggle(listItem, btn, wasCompleted) {
        const title = listItem.querySelector('h5');
        const icon = btn.querySelector('i');

        if (wasCompleted) {
            btn.classList.remove('btn-outline-success', 'btn-outline-warning', 'btn-outline-danger', 'btn-outline-orange');
            btn.classList.add('btn-success');
            icon.className = 'bi bi-check-circle-fill';
            if (title) {
                title.classList.add('text-decoration-line-through', 'text-muted');
            }
            completedCount++;
        } else {
            btn.classList.remove('btn-success', 'btn-outline-secondary');
            const originalClass = btn.dataset.originalClass || 'btn-outline-success';
            btn.classList.add(originalClass);
            icon.className = 'bi bi-circle';
            if (title) {
                title.classList.remove('text-decoration-line-through', 'text-muted');
            }
            completedCount--;
        }
        updateProgressBar();
    }

    /**
     * Increment habit with optimistic UI update
     */
    function incrementHabit(listItem, btn, url, extraData = {}) {
        const title = listItem.querySelector('h5');
        const icon = btn.querySelector('i');
        const countBadge = listItem.querySelector('.badge.bg-success, .badge.bg-danger');

        // Optimistic UI update - mark as done for today
        btn.classList.remove('btn-outline-success');
        btn.classList.add('btn-success');
        icon.className = 'bi bi-check-circle-fill';
        if (title) {
            title.classList.add('text-decoration-line-through', 'text-muted');
        }

        // Increment count badge
        if (countBadge) {
            const currentCount = parseInt(countBadge.textContent) || 0;
            countBadge.textContent = currentCount + 1;
            countBadge.classList.remove('bg-danger');
            countBadge.classList.add('bg-success');
        }

        completedCount++;
        updateProgressBar();

        // Background sync
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(extraData)
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Increment failed:', data.error);
                // Could revert here, but habit increments rarely fail
            } else if (data.count !== undefined && countBadge) {
                countBadge.textContent = data.count;
            }
        })
        .catch(error => {
            console.error('Increment error:', error);
        });
    }

    // Event delegation for all toggle buttons
    document.addEventListener('click', function(e) {
        // Find the button (may have clicked on icon inside)
        const btn = e.target.closest('button[type="submit"]');
        if (!btn) return;

        // Check if it's inside a toggle form
        const form = btn.closest('form');
        if (!form) return;

        const action = form.getAttribute('action') || '';

        // Handle todo toggle
        if (action.includes('/todos/') && action.includes('/toggle')) {
            e.preventDefault();
            const listItem = btn.closest('.list-group-item');
            if (listItem) {
                toggleItem(listItem, btn, action);
            }
            return;
        }

        // Handle daily toggle
        if (action.includes('/dailies/') && action.includes('/toggle')) {
            e.preventDefault();
            const listItem = btn.closest('.list-group-item');
            if (listItem) {
                // Check for target_date (tomorrow page)
                const targetDateInput = form.querySelector('input[name="target_date"]');
                const extraData = targetDateInput ? { target_date: targetDateInput.value } : {};
                toggleItem(listItem, btn, action, extraData);
            }
            return;
        }

        // Handle habit increment
        if (action.includes('/habits/') && action.includes('/increment')) {
            e.preventDefault();
            const listItem = btn.closest('.list-group-item');
            if (listItem) {
                const targetDateInput = form.querySelector('input[name="target_date"]');
                const extraData = targetDateInput ? { target_date: targetDateInput.value } : {};
                incrementHabit(listItem, btn, action, extraData);
            }
            return;
        }
    });

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', initCounts);
})();
