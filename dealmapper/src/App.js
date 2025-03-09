import Container from "react-bootstrap/Container";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ApiProvider from "./contexts/ApiProvider";
import Header from "./components/Header";
import RestaurantPage from "./pages/RestaurantPage";
import RestaurantsPage from "./pages/RestaurantsPage";
import DealsPage from "./pages/DealsPage";
import LoginPage from "./pages/LoginPage";

export default function App() {
  return (
    <Container fluid className="App">
      <BrowserRouter>
        <ApiProvider>
          <Header />
          <Routes>
            <Route path="/" element={<RestaurantsPage />} />
            <Route path="/deals" element={<DealsPage />} />
            <Route
              path="/restaurants/:restaurant_id"
              element={<RestaurantPage />}
            />
            <Route path="/login" element={<LoginPage />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </ApiProvider>
      </BrowserRouter>
    </Container>
  );
}
