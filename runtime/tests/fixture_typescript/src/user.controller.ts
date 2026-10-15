import { Controller, Get, Post } from '@nestjs/common';
import { UserService } from './user.service';

@Controller('users')
export class UserController {
  constructor(private readonly users: UserService) {}

  @Get()
  list() { return this.users.list(); }

  @Post()
  create() { return this.users.create(); }
}
