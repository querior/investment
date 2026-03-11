import React, { useState } from "react";
import { Button, Card, Form, Input, Typography } from "antd";
import { useDispatch, useSelector } from "react-redux";
import { loginRequest } from "../features/auth/reducer";
import type { RootState } from "../store/reducers";

export default function Login() {
	const dispatch = useDispatch();
	const { loading, error } = useSelector((s: RootState) => s.auth);
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");

	return (
		<div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
			<Card className="w-full max-w-md shadow">
				<Typography.Title level={3} className="!mb-4">
					Querior Quant
				</Typography.Title>

				<Form
					layout="vertical"
					onFinish={() => dispatch(loginRequest({ email, password }))}
				>
					<Form.Item label="Email" required>
						<Input
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							autoComplete="email"
						/>
					</Form.Item>
					<Form.Item label="Password" required>
						<Input.Password
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							autoComplete="current-password"
						/>
					</Form.Item>

					{error && <div className="text-red-600 mb-3">{error}</div>}

					<Button type="primary" htmlType="submit" loading={loading} block>
						Entra
					</Button>
				</Form>
			</Card>
		</div>
	);
}
