import { redirect } from "next/navigation";

// Root redirect → dashboard (or login if not authenticated)
export default function RootPage() {
  redirect("/dashboard");
}
