import { SESClient, SendEmailCommand } from "@aws-sdk/client-ses";

const ses = new SESClient({
    region: "us-east-1",
    maxAttempts: 1
});

function response(statusCode, message) {
    return {
        statusCode,
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message })
    };
}

export async function handler(event) {
    let input;

    try {
        input = JSON.parse(event.body);
    } catch {
        return response(400, "Request body must contain valid JSON.");
    }

    if (!input || typeof input !== "object" || Array.isArray(input)) {
        return response(400, "Request body must be a JSON object.");
    }

    const limits = {
        name: 100,
        email: 254,
        subject: 150,
        message: 5000
    };

    const contact = {};

    for (const [field, maxLength] of Object.entries(limits)) {
        if (typeof input[field] !== "string") {
            return response(400, `${field} must be text.`);
        }

        const value = input[field].trim();

        if (value.length === 0 || value.length > maxLength) {
            return response(
                400,
                `${field} must contain between 1 and ${maxLength} characters.`
            );
        }

        contact[field] = value;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailPattern.test(contact.email)) {
        return response(400, "Please provide a valid email address.");
    }

        const fromAddress = process.env.CONTACT_FROM_EMAIL;
    const toAddress = process.env.CONTACT_TO_EMAIL;

    if (!fromAddress || !toAddress) {
        return response(500, "Email service is not configured.");
    }

    // Keep header values on a single line.
    if (/[\r\n]/.test(contact.subject)) {
        return response(400, "Subject must be a single line.");
    }

    const command = new SendEmailCommand({
        Source: fromAddress,
        Destination: {
            ToAddresses: [toAddress]
        },
        ReplyToAddresses: [contact.email],
        Message: {
            Subject: {
                Data: `Portfolio enquiry: ${contact.subject}`,
                Charset: "UTF-8"
            },
            Body: {
                Text: {
                    Data: [
                        `Name: ${contact.name}`,
                        `Email: ${contact.email}`,
                        "",
                        contact.message
                    ].join("\n"),
                    Charset: "UTF-8"
                }
            }
        }
    });

    try {
        await ses.send(command);

        return response(
            200,
            "Your message was accepted for email delivery."
        );
    } catch (error) {
        // Log the error type without exposing the visitor's message.
        console.error("SES request failed", {
            name: error.name,
            message: error.message,
            requestId: error.$metadata?.requestId
        });

        return response(
            502,
            "Unable to confirm email submission. Please contact me using the email link."
        );
    }
}
