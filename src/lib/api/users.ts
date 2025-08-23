import { prisma } from "@/lib/db/prisma";
import bcrypt from "bcrypt";

export async function getUserByEmail(email: string) {
  try {
    return await prisma.user.findUnique({
      where: { email },
    });
  } catch (error) {
    console.error("Failed to fetch user:", error);
    return null;
  }
}

export async function getUserById(id: string) {
  try {
    return await prisma.user.findUnique({
      where: { id },
    });
  } catch (error) {
    console.error("Failed to fetch user:", error);
    return null;
  }
}

export async function createUser(data: {
  name: string;
  email: string;
  password: string;
}) {
  try {
    const hashedPassword = await bcrypt.hash(data.password, 10);

    return await prisma.user.create({
      data: {
        name: data.name,
        email: data.email,
        password: hashedPassword,
      },
    });
  } catch (error) {
    console.error("Failed to create user:", error);
    return null;
  }
}
