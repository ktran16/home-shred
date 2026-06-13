import createClient from "openapi-fetch";

import type { paths } from "./api.d";

// Relative baseUrl: the browser hits the FE origin, Next.js rewrites /api/* to
// the backend (SPEC §14.4). No CORS, no hardcoded backend host.
// Paths in the schema already include the "/api" prefix, so baseUrl is empty.
export const api = createClient<paths>({ baseUrl: "" });

// Convenience aliases for component-level schema types.
export type components = import("./api.d").components;
export type ExerciseOut = components["schemas"]["ExerciseOut"];
export type ProfileIn = components["schemas"]["ProfileIn"];
export type ProfileOut = components["schemas"]["ProfileOut"];
