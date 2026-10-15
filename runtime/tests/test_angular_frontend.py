from ases.pipeline import scan_project


def _write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_angular_source_is_frontend_not_express_or_server_templates(tmp_path):
    root = tmp_path / "angular-app"
    _write(root, "angular.json", '{}')
    _write(root, "src/app/home.component.ts", "import { UserService } from './api/user.service'; @Component({selector: 'app-home'}) export class HomeComponent {}")
    _write(root, "src/app/home.component.html", "<h1>Home</h1>")
    _write(root, "src/app/app.routes.ts", "export const routes = [{ path: '', component: HomeComponent }, { path: 'login', component: LoginComponent }];")
    _write(root, "src/app/api/user.service.ts", """import { HttpClient } from '@angular/common/http';
@Injectable() export class UserService {
  constructor(private http: HttpClient) {}
  load() { return this.http.get<User>('/api/users'); }
  save() { return this.http\n    .post<User>('/api/users', {}); }
}""")
    _write(root, "src/app/api/user.service.spec.ts", """test('query', () => {
  expect(query.get('tag')).toBe('tag');
});""")

    model = scan_project(root, tmp_path / "out")["semantic_model"]
    assert model["behaviors"] == []
    assert model["project"]["frameworks"] == ["Angular (observed from frontend source)"]
    assert len(model["frontend"]["components"]) == 1
    assert len(model["frontend"]["templates"]) == 1
    assert len(model["frontend"]["services"]) == 1
    assert {route["declared_path"] for route in model["frontend"]["routes"]} == {"", "login"}
    assert {(call["http_method"], call["path"]) for call in model["frontend"]["api_calls"]} == {
        ("GET", "/api/users"), ("POST", "/api/users")}
    assert any(f["pattern"] == "Angular Component Templates" for f in model["frontend_findings"])
    assert any("referenced by frontend modules" in f["reason"] for f in model["frontend_findings"] if f["pattern"] == "Frontend API Service Layer")
    assert not any(f["pattern"] == "Server-rendered Template UI" for f in model["frontend_findings"])
    assert model["source_classification"]["scopes"]["frontend"] >= 3
    sdd = (tmp_path / "out" / "docs" / "SDD.md").read_text(encoding="utf-8")
    assert "Observed frontend structure" in sdd
    assert "Angular Component Templates" in sdd
    assert "Frontend API Service Layer" in sdd
    odd = (tmp_path / "out" / "docs" / "ODD.md").read_text(encoding="utf-8")
    assert "Frontend architecture and conformance" in odd
    assert "Angular Component Templates" in odd
