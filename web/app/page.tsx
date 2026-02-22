import { redirect } from "next/navigation";

/**
 * Root page — redirects to the Dashboard.
 * All meaningful content lives under /dashboard.
 */
export default function RootPage() {
  redirect("/dashboard");
}
