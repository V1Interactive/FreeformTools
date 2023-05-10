namespace Freeform.Rigging.MocapCleanupDialogue
{
    using System;
    using System.Diagnostics;
    using System.Text.RegularExpressions;
    using System.Windows;
    using System.Windows.Input;
    using System.Windows.Interop;
    /// <summary>
    /// Interaction logic for MocapCleanupDialogue.xaml
    /// </summary>
    public partial class MocapCleanupDialogue : Window
    {
        public MocapCleanupDialogue()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public MocapCleanupDialogue(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            MocapCleanupDialogueVM vm = new MocapCleanupDialogueVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            MocapCleanupDialogueVM vm = DataContext as MocapCleanupDialogueVM;
            vm.Close();
        }

        private void TextInputFilter(object sender, TextCompositionEventArgs e)
        {
            Regex regex = new Regex("[^0-9.-]+");
            e.Handled = regex.IsMatch(e.Text);
        }
    }
}
