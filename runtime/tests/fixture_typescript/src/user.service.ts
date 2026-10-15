import { Injectable } from '@nestjs/common';

@Injectable()
export class UserService {
  list() { return prisma.user.findMany(); }
  create() { return prisma.user.create({ data: {} }); }
}
