
self.addEventListener("push", function (event) {
    let data = {
        title: "FreshTrack Reminder",
        body: "A food item is approaching its expiry date."
    };

    if (event.data) {
        try {
            data = { ...data, ...event.data.json() };
        } catch (error) {
            data.body = event.data.text();
        }
    }

    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: "/static/icon.png"
        })
    );
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();

    event.waitUntil(
        self.clients.openWindow("/")
    );
});
