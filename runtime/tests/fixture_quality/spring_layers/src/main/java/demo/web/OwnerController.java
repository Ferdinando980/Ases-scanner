package demo.web;
@Controller class OwnerController {
    private ClinicService clinicService;
    void show() { clinicService.load(); }
}
