const API_URL =
    "https://eva2a9pv06.execute-api.us-east-1.amazonaws.com/contact";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#contact-form");
    const submitButton = form && form.querySelector('button[type="submit"]');
    const statusMessage = document.querySelector("#contact-status");

    if (!form || !submitButton) {
        console.warn(
            "contact.js: #contact-form or its submit button not found — form submission disabled."
        );
        return;
    }

    let submitting = false;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (submitting) return;

        const formData = new FormData(form);

        const contact = {
            name: formData.get("name").trim(),
            email: formData.get("email").trim(),
            subject: formData.get("subject").trim(),
            message: formData.get("message").trim()
        };

        const hasEmptyField = Object.values(contact).some(
            (value) => value.length === 0
        );

        if (hasEmptyField) {
            statusMessage.textContent =
                "Please complete every field. Spaces alone do not count.";
            return;
        }

        submitting = true;
        submitButton.disabled = true;
        submitButton.textContent = "Sending…";
        statusMessage.textContent = "Submitting your message…";

        try {
            const result = await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(contact),
                signal: AbortSignal.timeout(20000)
            });

            const data = await result.json().catch(() => ({}));

            if (!result.ok) {
                if (result.status === 429) {
                    statusMessage.textContent =
                        "Too many requests. Please wait a moment before trying again.";
                } else if (result.status === 400) {
                    statusMessage.textContent =
                        data.message || "Please check your inputs.";
                } else {
                    statusMessage.textContent =
                        "Unable to confirm submission. Please use the email link below.";
                }

                return;
            }

            statusMessage.textContent =
                "Thank you. Your message was accepted for email delivery.";
            form.reset();
        } catch {
            statusMessage.textContent =
                "Unable to confirm submission. Your message may have been sent. Please use the email link below if needed.";
        } finally {
            submitting = false;
            submitButton.disabled = false;
            submitButton.textContent = "Send message";
        }
    });

    submitButton.disabled = false;
    statusMessage.textContent = "";
});
