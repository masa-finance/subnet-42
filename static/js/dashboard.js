document.addEventListener('DOMContentLoaded', function() {
    // Format timestamps to local time
    const timestamps = document.querySelectorAll('.timestamp');
    timestamps.forEach(function(timestamp) {
        const date = new Date(Number(timestamp.getAttribute('data-time')) * 1000);
        timestamp.textContent = date.toLocaleString();
    });

    // Add click handlers for collapsible sections
    const collapsibles = document.querySelectorAll('.collapsible-header');
    collapsibles.forEach(function(header) {
        header.addEventListener('click', function() {
            const content = this.nextElementSibling;
            if (content.style.maxHeight) {
                content.style.maxHeight = null;
                this.classList.remove('active');
            } else {
                content.style.maxHeight = content.scrollHeight + "px";
                this.classList.add('active');
            }
        });
    });

    // Refresh the data every 5 seconds
    function scheduleRefresh() {
        setTimeout(function() {
            refreshData();
            scheduleRefresh();
        }, 5000); // Refresh every 5 seconds
    }

    function refreshData() {
        fetch('/dashboard/data', {
            headers: {
                'X-API-Key': localStorage.getItem('apiKey') || '',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            updateDashboardData(data);
            // Add visual indication that data was refreshed
            const stats = document.querySelectorAll('.stat-box');
            stats.forEach(function(stat) {
                stat.classList.add('refreshing');
                setTimeout(() => stat.classList.remove('refreshing'), 1000);
            });
        })
        .catch(error => console.error('Error refreshing data:', error));
    }

    function updateDashboardData(data) {
        // Update worker count
        const workerCountElement = document.getElementById('worker-count');
        if (workerCountElement && data.worker_count !== undefined) {
            workerCountElement.textContent = data.worker_count;
        }

        // Update error count
        const errorCountElement = document.getElementById('error-count');
        if (errorCountElement && data.error_count_24h !== undefined) {
            errorCountElement.textContent = data.error_count_24h;
        }
        
        // Update uptime
        const uptimeElement = document.getElementById('uptime');
        if (uptimeElement && data.uptime_days !== undefined) {
            uptimeElement.textContent = data.uptime_days + ' days';
        }
        
        // Add last refresh time
        const lastRefreshElement = document.getElementById('last-refresh');
        if (lastRefreshElement) {
            const now = new Date();
            lastRefreshElement.textContent = now.toLocaleTimeString();
        }
    }

    // Store API key in local storage for future requests
    function storeApiKey() {
        const urlParams = new URLSearchParams(window.location.search);
        const apiKey = urlParams.get('api_key');
        if (apiKey) {
            localStorage.setItem('apiKey', apiKey);
            // Remove the API key from the URL
            urlParams.delete('api_key');
            const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
            window.history.replaceState({}, document.title, newUrl);
        }
    }

    storeApiKey();
    scheduleRefresh();
}); 