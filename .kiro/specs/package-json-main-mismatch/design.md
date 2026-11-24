# package.json `main` Field Mismatch Bugfix Design

## Overview

`backend/contact/package.json` declares `"main": "index.js"` but the actual Lambda entry file is `index.mjs`. Any tooling that resolves the package entry point via the `main` field (bundlers, test runners, `require`/dynamic `import` with package resolution, AWS SAM local, etc.) will attempt to load a non-existent `index.js` and fail. The fix is a one-field update: change `"main"` from `"index.js"` to `"index.mjs"`.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — a tool or runtime resolves the `contact` package entry point using the `"main"` field and attempts to load `index.js`, which does not exist.
- **Property (P)**: The desired outcome — the resolved entry file is `index.mjs`, which exists and is the correct ES-module Lambda handler.
- **Preservation**: All other fields in `package.json` (`name`, `version`, `description`, `scripts`, `keywords`, `author`, `license`, `dependencies`) must remain unchanged by the fix.
- **index.mjs**: The actual Lambda handler file at `backend/contact/index.mjs`. It is an ES module (`.mjs` extension, `"type"` field absent from package.json meaning `"commonjs"` is the default, but `.mjs` forces ES-module parsing regardless).
- **`main` field**: The `package.json` field that Node.js and most tooling use as the default entry point when resolving a package.

## Bug Details

### Bug Condition

The bug manifests when any tool or runtime reads `backend/contact/package.json` and uses the `"main"` field to locate the entry file. It resolves `index.js`, finds no such file, and fails (module-not-found error or equivalent).

**Formal Specification:**
```
FUNCTION isBugCondition(packageJson)
  INPUT: packageJson — parsed contents of backend/contact/package.json
  OUTPUT: boolean

  declaredMain  := packageJson["main"]
  actualEntry   := fileExistsInPackageDir("index.mjs")
  wrongEntry    := NOT fileExistsInPackageDir(declaredMain)

  RETURN declaredMain IS NOT "index.mjs"
         AND actualEntry IS true
         AND wrongEntry IS true
END FUNCTION
```

### Examples

- **Bundler resolves package entry**: Webpack/esbuild reads `"main": "index.js"`, attempts `require("./index.js")`, gets `MODULE_NOT_FOUND`; build fails.
- **AWS SAM local invoke**: SAM resolves the handler module via `package.json`; `index.js` missing causes invocation failure.
- **Jest/Vitest test run targeting the package**: Test runner imports the package; resolution fails before any test executes.
- **`node -e "require('./backend/contact')`**: Node resolves `index.js`, throws `Error: Cannot find module './index.js'`.
- **Happy path after fix**: `"main": "index.mjs"` resolves correctly; `index.mjs` loads as an ES module.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- All other `package.json` fields (`name`, `version`, `description`, `scripts`, `keywords`, `author`, `license`, `dependencies`) must remain exactly as they are.
- The `index.mjs` source file itself must not be modified.
- The Lambda deployment artifact and handler configuration (`index.handler` in AWS) must not be changed — only the `package.json` metadata is updated.

**Scope:**
Only the `"main"` field value changes. No other file in the repository is affected by this fix.

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **Copy-paste from default template**: `npm init` generates `"main": "index.js"` by default. The developer renamed or created the file as `index.mjs` (to use ES module syntax required by the Lambda runtime) but did not update `package.json`.

2. **No validation step in CI**: The deployment workflow does not verify that the `main` field resolves to an existing file, so the mismatch went undetected.

3. **Lambda runtime does not use `main` directly**: AWS Lambda invokes the handler via its own configuration (`index.handler`), not via Node's package resolution, so the bug is silent in production but would surface in any local tooling or testing scenario.

## Correctness Properties

Property 1: Bug Condition - `main` Field Resolves to Existing File

_For any_ tool or runtime that reads `backend/contact/package.json` and resolves the `"main"` field, the fixed `package.json` SHALL point to a file that exists (`index.mjs`), so resolution succeeds without a module-not-found error.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - All Other Fields Unchanged

_For any_ field in `backend/contact/package.json` other than `"main"`, the fixed file SHALL contain exactly the same value as the original file, preserving all dependency declarations, scripts, and metadata.

**Validates: Requirements 3.1, 3.2**

## Fix Implementation

### Changes Required

**File**: `backend/contact/package.json`

**Specific Changes**:

1. **Update `"main"` field**: Change the value from `"index.js"` to `"index.mjs"`.

   Before:
   ```json
   "main": "index.js",
   ```

   After:
   ```json
   "main": "index.mjs",
   ```

No other changes are needed anywhere in the repository.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the broken resolution on the unfixed `package.json`, then verify the fix resolves correctly and preserves all other fields.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the resolution failure BEFORE applying the fix.

**Test Plan**: Read the unfixed `package.json`, resolve the `main` field to a file path, and assert that the file exists. Run on UNFIXED file to observe the failure.

**Test Cases**:
1. **Resolve `main` field on unfixed file**: Read `package.json`, check `fileExists(main)` → `false` for `"index.js"` (will fail on unfixed file).
2. **Node resolution attempt**: Run `node -e "require('./backend/contact')"` on unfixed code → `MODULE_NOT_FOUND` error (will fail on unfixed file).
3. **`main` matches actual entry**: Assert `package.json["main"] === "index.mjs"` (will fail on unfixed file).
4. **Other fields intact**: Assert all other fields have expected values (should pass on both unfixed and fixed file).

**Expected Counterexamples**:
- `Error: Cannot find module './index.js'` when Node resolves the unfixed `main` field.
- `fileExists("index.js")` returns `false` while `fileExists("index.mjs")` returns `true`.

### Fix Checking

**Goal**: Verify that after the fix, the `main` field resolves to an existing file with the correct content.

**Pseudocode:**
```
FOR ALL packageJson WHERE isBugCondition(packageJson) DO
  fixedPackageJson := applyFix(packageJson)
  ASSERT fixedPackageJson["main"] = "index.mjs"
  ASSERT fileExistsInPackageDir(fixedPackageJson["main"]) = true
END FOR
```

### Preservation Checking

**Goal**: Verify that all fields other than `"main"` are identical before and after the fix.

**Pseudocode:**
```
FOR ALL field WHERE field IS NOT "main" DO
  ASSERT packageJson_original[field] = packageJson_fixed[field]
END FOR
```

**Testing Approach**: A simple structural comparison of the JSON objects is sufficient here — the input domain is a single well-defined JSON file, so exhaustive field-by-field assertion is both practical and complete.

**Test Plan**: Read the original `package.json`, apply the fix, then compare field-by-field.

**Test Cases**:
1. **`name` field preserved**: `fixed["name"] === original["name"]`.
2. **`version` field preserved**: `fixed["version"] === original["version"]`.
3. **`dependencies` field preserved**: `fixed["dependencies"]` deep-equals `original["dependencies"]`.
4. **No new fields added**: `Object.keys(fixed)` equals `Object.keys(original)`.

### Unit Tests

- Assert `package.json["main"]` equals `"index.mjs"` after fix.
- Assert `index.mjs` exists in `backend/contact/`.
- Assert `index.js` does NOT exist in `backend/contact/` (confirms the original mismatch source is gone).
- Assert all other `package.json` fields are unchanged.

### Property-Based Tests

- Generate all field names in `package.json` and verify only `"main"` differs between original and fixed versions.
- For any tool simulation that reads `main` and checks file existence, verify resolution succeeds for all valid package states.

### Integration Tests

- Run `node -e "import('./backend/contact/index.mjs').then(() => console.log('ok'))"` — verify the module loads without error after fix.
- Verify the `@aws-sdk/client-ses` dependency declared in `package.json` is still resolvable from the fixed file.
