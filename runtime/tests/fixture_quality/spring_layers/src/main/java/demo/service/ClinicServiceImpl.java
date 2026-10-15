package demo.service;
@Service class ClinicServiceImpl implements ClinicService {
    private OwnerRepository ownerRepository;
    public void load() { ownerRepository.findAll(); }
}
