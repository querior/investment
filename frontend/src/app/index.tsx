import ChatWidget from "../components/chat";
import router from "./router";
import { RouterProvider } from "react-router-dom";

const App = () => {
	return (
		<>
			<RouterProvider router={router} />
			<ChatWidget />
		</>
	);
};

export default App;
