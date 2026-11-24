# Bugfix Requirements Document

## Introduction

Two bugs affect the contact form feature of this AWS portfolio static website. The first causes the contact form submit button to remain permanently disabled because `contact.js` queries DOM elements at the top level before the DOM is ready, throwing a TypeError that prevents the enable-button line from ever running. The second is a `package.json` `"main"` field mismatch in the Lambda backend: it points to `index.js` while the actual entry file is `index.mjs`, which can break any tooling that resolves the package entry point.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `contact.js` is executed before the DOM is fully parsed (or `#contact-form` is absent) THEN the system throws a TypeError on `form.querySelector(...)` because `form` is `null`, halting all further script execution

1.2 WHEN the TypeError halts script execution THEN the system never reaches `submitButton.disabled = false`, leaving the submit button in its hardcoded `disabled` state permanently

1.3 WHEN tooling (bundler, Lambda runtime resolver, or test runner) reads `backend/contact/package.json` to resolve the package entry point THEN the system resolves `index.js`, which does not exist, instead of the actual entry file `index.mjs`

### Expected Behavior (Correct)

2.1 WHEN `contact.js` executes and `#contact-form` or the submit button element is not found in the DOM THEN the system SHALL log a console warning and exit early without throwing an uncaught TypeError

2.2 WHEN `contact.js` executes and both `#contact-form` and the submit button are found THEN the system SHALL enable the submit button and attach the submit event listener, making the form fully functional

2.3 WHEN tooling reads `backend/contact/package.json` to resolve the package entry point THEN the system SHALL resolve `index.mjs`, the actual Lambda handler file

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the contact form is submitted with all fields filled THEN the system SHALL CONTINUE TO POST the form data to the API and display a success or error status message

3.2 WHEN the contact form is submitted with one or more empty fields THEN the system SHALL CONTINUE TO block submission and display a validation message

3.3 WHEN a form submission is already in progress THEN the system SHALL CONTINUE TO disable the submit button and prevent duplicate submissions until the request completes

3.4 WHEN the API returns a 429 or 400 response THEN the system SHALL CONTINUE TO display the appropriate error message to the user

3.5 WHEN the fetch request throws or times out THEN the system SHALL CONTINUE TO display the fallback error message and re-enable the submit button via the `finally` block
