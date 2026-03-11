import { useState } from "react";
import { FloatButton, Input, Avatar } from "antd";
import { MessageOutlined, CloseOutlined } from "@ant-design/icons";

type Message = {
	role: "user" | "assistant";
	content: string;
};

export default function ChatWidget() {
	const [open, setOpen] = useState(false);
	const [messages, setMessages] = useState<Message[]>([
		{ role: "assistant", content: "Hi 👋 How can I help you?" },
	]);
	const [input, setInput] = useState("");

	const sendMessage = () => {
		if (!input.trim()) return;

		const userMessage: Message = { role: "user", content: input };

		setMessages((prev) => [...prev, userMessage]);

		// Mock risposta assistant
		setTimeout(() => {
			setMessages((prev) => [
				...prev,
				{ role: "assistant", content: "This is a mock response." },
			]);
		}, 600);

		setInput("");
	};

	return (
		<>
			{/* Floating Button */}
			<FloatButton
				icon={<MessageOutlined />}
				type="primary"
				style={{ right: 24, bottom: 24 }}
				onClick={() => setOpen(true)}
			/>

			{/* Overlay Chat Panel */}
			{open && (
				<div
					style={{
						position: "fixed",
						bottom: 24,
						right: 24,
						width: 380,
						height: 520,
						background: "white",
						borderRadius: 16,
						boxShadow: "0 15px 50px rgba(0,0,0,0.25)",
						display: "flex",
						flexDirection: "column",
						zIndex: 2000,
					}}
				>
					{/* Header */}
					<div
						style={{
							padding: "12px 16px",
							borderBottom: "1px solid #f0f0f0",
							display: "flex",
							justifyContent: "space-between",
							alignItems: "center",
							fontWeight: 600,
						}}
					>
						Assistant
						<CloseOutlined
							onClick={() => setOpen(false)}
							style={{ cursor: "pointer" }}
						/>
					</div>

					{/* Messages */}
					<div
						style={{
							flex: 1,
							padding: 16,
							overflowY: "auto",
							display: "flex",
							flexDirection: "column",
							gap: 12,
						}}
					>
						{messages.map((msg, i) => (
							<div
								key={i}
								style={{
									display: "flex",
									justifyContent:
										msg.role === "user" ? "flex-end" : "flex-start",
								}}
							>
								{msg.role === "assistant" && (
									<Avatar size="small" style={{ marginRight: 8 }}>
										AI
									</Avatar>
								)}

								<div
									style={{
										maxWidth: "70%",
										padding: "8px 12px",
										borderRadius: 12,
										background: msg.role === "user" ? "#1677ff" : "#f5f5f5",
										color: msg.role === "user" ? "white" : "black",
									}}
								>
									{msg.content}
								</div>
							</div>
						))}
					</div>

					{/* Input */}
					<div style={{ padding: 12, borderTop: "1px solid #f0f0f0" }}>
						<Input.Search
							placeholder="Type a message..."
							value={input}
							onChange={(e) => setInput(e.target.value)}
							onSearch={sendMessage}
							enterButton="Send"
						/>
					</div>
				</div>
			)}
		</>
	);
}
