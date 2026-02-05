import Header from "./components/Header/Header";
import Stepper from "../src/Stepper/Stepper";
import AppRoutes from "../src/router/AppRouter";

export default function App() {
  return (
    <>
      <Header />
      <Stepper />
      <AppRoutes />
    </>
  );
}
