import { isAuthenticated } from "./auth";

export type Route =
  | { name: "login" }
  | { name: "library" }
  | { name: "reader"; id: string }
  | { name: "search" }
  | { name: "analytics" }
  | { name: "settings" };

type RouteHandler = (route: Route) => void;

const handlers: RouteHandler[] = [];

export function onRoute(handler: RouteHandler): void {
  handlers.push(handler);
}

export function parseHash(hash: string): Route {
  const h = hash.replace(/^#\/?/, "");
  if (!h || h === "login") return { name: "login" };
  if (h === "library") return { name: "library" };
  if (h.startsWith("reader/")) return { name: "reader", id: h.slice(7) };
  if (h === "search") return { name: "search" };
  if (h === "analytics") return { name: "analytics" };
  if (h === "settings") return { name: "settings" };
  return { name: "login" };
}

export function navigate(path: string): void {
  window.location.hash = path;
}

export function initRouter(): void {
  const dispatch = () => {
    let route = parseHash(window.location.hash);
    // Auth guard
    if (route.name !== "login" && !isAuthenticated()) {
      route = { name: "login" };
      window.location.hash = "/login";
    }
    for (const h of handlers) h(route);
  };

  window.addEventListener("hashchange", dispatch);
  // Initial dispatch
  dispatch();
}
