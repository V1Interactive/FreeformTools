namespace Freeform.Rigging.ParticleConstraintDialogue
{
    using System;
    using System.Diagnostics;
    using System.Text.RegularExpressions;
    using System.Windows;
    using System.Windows.Input;
    using System.Windows.Interop;


    /// <summary>
    /// Interaction logic for ParticleConstraintDialogue.xaml
    /// </summary>
    public partial class ParticleConstraintDialogue : Window
    {
        public ParticleConstraintDialogue()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public ParticleConstraintDialogue(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            ParticleConstraintDialogueVM vm = new ParticleConstraintDialogueVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            ParticleConstraintDialogueVM vm = DataContext as ParticleConstraintDialogueVM;
            vm.Close();
        }

        private void TextInputFilter(object sender, TextCompositionEventArgs e)
        {
            Regex regex = new Regex("[^0-9.-]+");
            e.Handled = regex.IsMatch(e.Text);
        }
    }
}
