(function () {
            const shell = document.querySelector("[data-admin-notifications]");
            if (!shell) {
                return;
            }

            const endpoint = shell.dataset.url;
            const reservationsUrl = shell.dataset.reservationsUrl;
            const financeUrl = shell.dataset.financeUrl;
            const bell = shell.querySelector(".notification-bell");
            const count = shell.querySelector("[data-notification-count]");
            const dropdown = shell.querySelector("[data-notification-dropdown]");
            const list = shell.querySelector("[data-notification-list]");
            const subtitle = shell.querySelector("[data-notification-subtitle]");
            const toastStack = document.querySelector("[data-notification-toasts]");
            const reservationStorageKey = "adminReservationLastSeenId";
            const fixedChargeStorageKey = "adminFixedChargeSeenAlerts";

            function setCount(total, reservationCount, fixedChargeCount) {
                count.textContent = total;
                count.hidden = total <= 0;

                if (total <= 0) {
                    subtitle.textContent = "No pending admin notifications";
                    return;
                }

                const parts = [];
                if (reservationCount > 0) {
                    parts.push(reservationCount + " reservation(s)");
                }
                if (fixedChargeCount > 0) {
                    parts.push(fixedChargeCount + " finance alert(s)");
                }
                subtitle.textContent = parts.join(" • ");
            }

            function renderNotifications(reservations, fixedChargeAlerts) {
                const chunks = [];

                if (reservations.length) {
                    chunks.push('<p class="notification-section-label">Reservations</p>');
                    chunks.push(reservations.map(function (item) {
                        return (
                            '<div class="notification-item">' +
                                '<strong>Reservation #' + item.id + ' - ' + item.vehicle_name + '</strong>' +
                                '<p>' + item.client_name + ' | ' + item.start_date + ' to ' + item.end_date + '</p>' +
                                '<p>Received ' + item.created_at + '</p>' +
                            '</div>'
                        );
                    }).join(""));
                }

                if (fixedChargeAlerts.length) {
                    chunks.push('<p class="notification-section-label">Finance</p>');
                    chunks.push(fixedChargeAlerts.map(function (item) {
                        return (
                            '<div class="notification-item">' +
                                '<strong>' + item.category_label + ' - ' + item.vehicle_name + '</strong>' +
                                '<p>' + item.due_text + ' | Due ' + item.due_date + '</p>' +
                                '<p>' + (item.amount_display || '$0.00') + '</p>' +
                            '</div>'
                        );
                    }).join(""));
                }

                if (!chunks.length) {
                    list.innerHTML = '<p class="notification-empty">No pending admin notifications right now.</p>';
                    return;
                }

                list.innerHTML = chunks.join("");
            }

            function showToast(title, body) {
                if (!toastStack) {
                    return;
                }

                const toast = document.createElement("div");
                toast.className = "notification-toast";
                toast.innerHTML = "<strong>" + title + "</strong><p>" + body + "</p>";
                toastStack.appendChild(toast);

                window.setTimeout(function () {
                    toast.remove();
                }, 5000);
            }

            function showBrowserNotification(title, body, targetUrl) {
                if (!("Notification" in window) || Notification.permission !== "granted") {
                    return;
                }

                const notification = new Notification(title, { body: body });
                notification.onclick = function () {
                    window.open(targetUrl, "_self");
                };
            }

            async function loadNotifications() {
                const storedReservationId = window.localStorage.getItem(reservationStorageKey);
                const sinceId = storedReservationId ? Number(storedReservationId) : 0;
                const storedFixedChargeKeys = JSON.parse(window.localStorage.getItem(fixedChargeStorageKey) || "[]");

                const response = await fetch(endpoint + "?since_id=" + sinceId, {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });

                if (!response.ok) {
                    return;
                }

                const data = await response.json();
                const recentReservations = data.recent_pending || [];
                const fixedChargeAlerts = data.fixed_charge_alerts || [];
                const reservationCount = data.pending_count || 0;
                const fixedChargeCount = data.fixed_charge_count || 0;

                setCount(data.total_count || (reservationCount + fixedChargeCount), reservationCount, fixedChargeCount);
                renderNotifications(recentReservations, fixedChargeAlerts);

                if (!storedReservationId) {
                    window.localStorage.setItem(reservationStorageKey, String(data.latest_id || 0));
                    window.localStorage.setItem(
                        fixedChargeStorageKey,
                        JSON.stringify(fixedChargeAlerts.map(function (item) { return item.alert_key; }))
                    );
                    return;
                }

                (data.new_reservations || []).forEach(function (item) {
                    const body = item.client_name + " reserved " + item.vehicle_name;
                    showToast("New reservation", body);
                    showBrowserNotification("New reservation", body, reservationsUrl);
                });

                const unseenFixedChargeAlerts = fixedChargeAlerts.filter(function (item) {
                    return storedFixedChargeKeys.indexOf(item.alert_key) === -1;
                });

                unseenFixedChargeAlerts.forEach(function (item) {
                    showToast("Finance alert", item.notification_text);
                    showBrowserNotification("Finance alert", item.notification_text, financeUrl);
                });

                window.localStorage.setItem(reservationStorageKey, String(data.latest_id || sinceId));
                window.localStorage.setItem(
                    fixedChargeStorageKey,
                    JSON.stringify(fixedChargeAlerts.map(function (item) { return item.alert_key; }))
                );
            }

            bell.addEventListener("click", function () {
                dropdown.classList.toggle("is-open");
                if ("Notification" in window && Notification.permission === "default") {
                    Notification.requestPermission();
                }
            });

            document.addEventListener("click", function (event) {
                if (!shell.contains(event.target)) {
                    dropdown.classList.remove("is-open");
                }
            });

            loadNotifications();
            window.setInterval(loadNotifications, 10000);
        })();