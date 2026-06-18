import { isAuthenticated } from "./auth";

export type Route =
  | { name: "login" }
  | { name: "home" }
  | { name: "event"; id: string }
  | { name: "leaderboard" }
  | { name: "history" }
  | { name: "settings" };

type RouteHandler = (route: Route) => void;

const handlers: RouteHandler[] = [];

export function onRoute(handler: RouteHandler): void {
  handlers.push(handler);
}

export function parseHash(hash: string): Route {
  const h = hash.replace(/^#\/?/, "");
  if (!h || h === "login") return { name: "login" };
  if (h === "home" || h === "") return { name: "home" };
  if (h.startsWith("event/")) return { name: "event", id: h.slice(6) };
  if (h === "leaderboard") return { name: "leaderboard" };
  if (h === "history") return { name: "history" };
  if (h === "settings") return { name: "settings" };
  return { name: "home" };
}

export function navigate(path: string): void {
  window.location.hash = path;
}

export function initRouter(): void {
  const dispatch = () => {
    let route = parseHash(window.location.hash);
    if (route.name !== "login" && !isAuthenticated()) {
      route = { name: "login" };
      window.location.hash = "/login";
    }
    for (const h of handlers) h(route);
  };

  window.addEventListener("hashchange", dispatch);
  dispatch();
}
